import os
from datetime import date, datetime, time, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.database import get_db
from app.main import create_app
from app.models import Booking, BookingStatus, Facility, Slot, Sport, User
from app.seed import seed


@pytest.fixture
def catalogue(connection):
    with Session(connection) as db, db.begin():
        # Stable future dates, independent of the event demo data and today's date.
        seed(db, date(2099, 9, 25), test_users=2)
    app = create_app(os.environ.get("TEST_DATABASE_URL"))

    def isolated_db():
        with Session(connection) as db:
            yield db

    app.dependency_overrides[get_db] = isolated_db
    with TestClient(app) as client:
        yield client


def test_sports_and_facility_filtering(catalogue):
    response = catalogue.get("/api/sports")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    sports = response.json()
    assert [s["name"] for s in sports] == ["Badminton", "Football", "Tennis"]
    assert set(sports[0]) == {"id", "name", "description"}
    for sport in sports:
        result = catalogue.get("/api/facilities", params={"sport_id": sport["id"]})
        assert result.status_code == 200
        assert len(result.json()) == {"Badminton": 10, "Football": 0, "Tennis": 1}[sport["name"]]
        assert all(f["sport_id"] == sport["id"] and f["is_active"] for f in result.json())


def test_slots_filtered_ordered_and_serialized(catalogue):
    first = catalogue.get("/api/facilities?sport_id=1").json()[0]
    result = catalogue.get("/api/slots", params={"facility_id": first["id"], "date": "2099-09-25"})
    assert result.status_code == 200
    assert result.headers["cache-control"] == "no-store"
    rows = result.json()
    assert len(rows) == 5
    assert [row["start_time"] for row in rows] == [f"{h}:00:00" for h in range(16, 21)]
    assert all(row["facility_id"] == first["id"] and row["date"] == "2099-09-25" and row["status"] == "AVAILABLE" for row in rows)
    assert set(rows[0]) == {"id", "facility_id", "date", "start_time", "end_time", "status"}
    assert catalogue.get("/api/slots", params={"facility_id": first["id"], "date": "2099-10-01"}).json() == []


def test_booking_and_cancel_change_availability(catalogue, connection):
    with Session(connection) as db:
        slot = db.scalars(select(Slot).order_by(Slot.id)).first()
        params = {"facility_id": slot.facility_id, "date": str(slot.slot_date)}
        slot_id = slot.id
        booking = Booking(slot_id=slot.id, user_id=db.scalar(select(User.id).limit(1)), idempotency_key="catalogue-check")
        db.add(booking)
        db.commit()
        booking_id = booking.id
    rows = catalogue.get("/api/slots", params=params).json()
    assert next(r for r in rows if r["id"] == slot_id)["status"] == "BOOKED"
    assert sum(r["status"] == "AVAILABLE" for r in rows) == 4
    with Session(connection) as db:
        booking = db.get(Booking, booking_id)
        booking.status = BookingStatus.CANCELLED
        booking.cancelled_at = datetime.now(timezone.utc)
        db.commit()
    assert all(r["status"] == "AVAILABLE" for r in catalogue.get("/api/slots", params=params).json())


def test_inactive_facility_is_not_offered(catalogue, connection):
    with Session(connection) as db:
        facility = db.scalars(select(Facility).order_by(Facility.id)).first()
        facility.is_active = False
        facility_id, sport_id = facility.id, facility.sport_id
        db.commit()
    assert facility_id not in [r["id"] for r in catalogue.get(f"/api/facilities?sport_id={sport_id}").json()]
    response = catalogue.get("/api/slots", params={"facility_id": facility_id, "date": "2099-09-25"})
    assert len(response.json()) == 5
    assert all(r["status"] == "UNAVAILABLE" for r in response.json())


def test_past_and_started_slots_are_unavailable(catalogue, connection):
    with Session(connection) as db:
        facility_id = db.scalar(select(Facility.id).limit(1))
        now_ist = db.scalar(select(text("timezone('Asia/Kolkata', statement_timestamp())")))
        start = time(now_ist.hour)
        # Approved schema excludes midnight-crossing slots; at 23:xx test 22:00.
        hour = min(start.hour, 22)
        for day in (date(2000, 1, 1), now_ist.date()):
            db.add(Slot(facility_id=facility_id, slot_date=day, start_time=time(hour), end_time=time(hour + 1)))
        db.commit()
    for day in (date(2000, 1, 1), now_ist.date()):
        response = catalogue.get("/api/slots", params={"facility_id": facility_id, "date": str(day)})
        assert response.status_code == 200
        assert response.json()[0]["status"] == "UNAVAILABLE"


@pytest.mark.parametrize("url", [
    "/api/facilities", "/api/facilities?sport_id=0", "/api/facilities?sport_id=-1",
    "/api/facilities?sport_id=abc", "/api/facilities?sport_id=9223372036854775808",
    "/api/slots?facility_id=1", "/api/slots?date=2099-09-25",
    "/api/slots?facility_id=0&date=2099-09-25", "/api/slots?facility_id=1&date=wrong",
    "/api/slots?facility_id=1&date=2099-02-30",
])
def test_invalid_queries(catalogue, url):
    assert catalogue.get(url).status_code == 422


@pytest.mark.parametrize("url,message", [
    ("/api/facilities?sport_id=999999", "Sport not found"),
    ("/api/slots?facility_id=999999&date=2099-09-25", "Facility not found"),
])
def test_missing_parent(catalogue, url, message):
    response = catalogue.get(url)
    assert response.status_code == 404
    assert response.json() == {"detail": message}


def test_empty_catalogue(connection):
    app = create_app()
    def empty_db():
        with Session(connection) as db:
            yield db
    app.dependency_overrides[get_db] = empty_db
    with TestClient(app) as client:
        assert client.get("/api/sports").json() == []


def test_catalogue_database_failure_and_openapi():
    with TestClient(create_app("postgresql+psycopg://invalid:secret@127.0.0.1:1/missing")) as client:
        for path in ("/api/sports", "/api/facilities?sport_id=1", "/api/slots?facility_id=1&date=2099-09-25"):
            response = client.get(path)
            assert response.status_code == 503
            assert response.json() == {"detail": "Database temporarily unavailable"}
        paths = client.get("/openapi.json").json()["paths"]
        assert all(path in paths for path in ("/api/sports", "/api/facilities", "/api/slots"))
