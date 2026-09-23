"""Real PostgreSQL tests for the booking HTTP contract and simultaneous callers."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.database import build_engine, get_db
from app.main import create_app
from app.models import Base, Booking, BookingStatus, Facility, Slot, User
from app.seed import seed


@pytest.fixture
def booking_app(monkeypatch):
    """Independent pool and schema so simultaneous requests use real connections."""
    admin = build_engine()
    schema = "test_slotgrab_" + uuid4().hex
    with admin.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(admin.url, pool_size=25, max_overflow=30, pool_timeout=20,
                           connect_args={"connect_timeout": 3,
                                         "options": f"-c search_path={schema}"})
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db, db.begin():
            seed(db, date(2099, 9, 25), test_users=50)
        app = create_app()
        sessions = sessionmaker(engine, expire_on_commit=False)

        def isolated_db():
            with sessions() as db:
                yield db

        app.dependency_overrides[get_db] = isolated_db
        monkeypatch.setenv("SLOTGRAB_DEMO_MODE", "1")
        with TestClient(app) as client:
            yield client, sessions
    finally:
        engine.dispose()
        with admin.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def slot_and_users(sessions):
    with sessions() as db:
        return (db.scalar(select(Slot.id).order_by(Slot.id)),
                list(db.scalars(select(User.id).order_by(User.id))))


def post(client, slot_id, user_id, key=None):
    return client.post("/api/bookings", headers={"X-Demo-User-Id": str(user_id)},
                       json={"slot_id": slot_id, "idempotency_key": str(key or uuid4())})


def test_create_retry_conflict_and_catalogue_status(booking_app):
    client, sessions = booking_app
    slot_id, users = slot_and_users(sessions)
    listed = client.get("/api/demo/users")
    assert listed.status_code == 200 and len(listed.json()) == 50
    assert listed.json()[0] == {"id": users[0], "name": "Synthetic Demo User 001"}
    key = uuid4()
    first = post(client, slot_id, users[0], key)
    assert first.status_code == 201
    assert first.headers["cache-control"] == "no-store"
    assert set(first.json()) == {"id", "slot_id", "status", "created_at"}
    assert first.json()["slot_id"] == slot_id and first.json()["status"] == "CONFIRMED"
    retry = post(client, slot_id, users[0], key)
    assert retry.status_code == 200 and retry.json() == first.json()
    conflict = post(client, slot_id, users[1])
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "SLOT_ALREADY_BOOKED"
    with sessions() as db:
        count = db.scalar(select(func.count()).select_from(Booking).where(Booking.slot_id == slot_id))
        slot = db.get(Slot, slot_id)
    assert count == 1
    rows = client.get("/api/slots", params={"facility_id": slot.facility_id, "date": str(slot.slot_date)}).json()
    assert next(row for row in rows if row["id"] == slot_id)["status"] == "BOOKED"


def test_reused_key_for_another_slot_and_cancelled_original(booking_app):
    client, sessions = booking_app
    slot_id, users = slot_and_users(sessions)
    with sessions() as db:
        other_id = db.scalar(select(Slot.id).where(Slot.id != slot_id).order_by(Slot.id))
    key = uuid4()
    created = post(client, slot_id, users[0], key)
    assert created.status_code == 201
    reused = post(client, other_id, users[0], key)
    assert reused.status_code == 409 and reused.json()["code"] == "IDEMPOTENCY_KEY_REUSED"
    with sessions() as db, db.begin():
        booking = db.get(Booking, created.json()["id"])
        booking.status = BookingStatus.CANCELLED
        booking.cancelled_at = db.scalar(select(func.now()))
    cancelled_retry = post(client, slot_id, users[0], key)
    assert cancelled_retry.status_code == 409
    assert cancelled_retry.json()["code"] == "REQUEST_ALREADY_CANCELLED"
    assert post(client, slot_id, users[1]).status_code == 201


def test_demo_guard_and_validation(booking_app, monkeypatch):
    client, sessions = booking_app
    slot_id, users = slot_and_users(sessions)
    body = {"slot_id": slot_id, "idempotency_key": str(uuid4())}
    assert client.post("/api/bookings", json=body).status_code == 401
    assert post(client, slot_id, 999999).status_code == 401
    for value in (0, -1, 9223372036854775808):
        assert post(client, value, users[0]).status_code == 422
    assert post(client, 999999, users[0]).status_code == 404
    assert client.post("/api/bookings", headers={"X-Demo-User-Id": str(users[0])},
                       json={"slot_id": slot_id, "idempotency_key": "bad"}).status_code == 422
    monkeypatch.delenv("SLOTGRAB_DEMO_MODE")
    disabled = post(client, slot_id, users[0])
    assert disabled.status_code == 403 and disabled.json()["code"] == "DEMO_DISABLED"
    assert client.get("/api/demo/users").status_code == 403
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(Booking)) == 0


def test_inactive_and_started_rejected(booking_app):
    client, sessions = booking_app
    slot_id, users = slot_and_users(sessions)
    with sessions() as db, db.begin():
        facility_id = db.get(Slot, slot_id).facility_id
        db.get(Facility, facility_id).is_active = False
    blocked = post(client, slot_id, users[0])
    assert blocked.status_code == 409 and blocked.json()["code"] == "SLOT_UNAVAILABLE"
    with sessions() as db, db.begin():
        db.get(Facility, facility_id).is_active = True
        db.get(Slot, slot_id).slot_date = date(2000, 1, 1)
    past = post(client, slot_id, users[0])
    assert past.status_code == 409 and past.json()["code"] == "SLOT_UNAVAILABLE"


def test_fifty_simultaneous_users_get_one_winner(booking_app):
    client, sessions = booking_app
    slot_id, users = slot_and_users(sessions)
    with ThreadPoolExecutor(max_workers=50) as pool:
        responses = list(pool.map(lambda user: post(client, slot_id, user), users))
    counts = Counter(response.status_code for response in responses)
    assert counts == {201: 1, 409: 49}
    assert all(r.json()["code"] == "SLOT_ALREADY_BOOKED" for r in responses if r.status_code == 409)
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(Booking).where(
            Booking.slot_id == slot_id, Booking.status == BookingStatus.CONFIRMED)) == 1


def test_concurrent_retry_same_key_and_different_slot(booking_app):
    client, sessions = booking_app
    first_slot, users = slot_and_users(sessions)
    with sessions() as db:
        second_slot = db.scalar(select(Slot.id).where(Slot.id != first_slot).order_by(Slot.id))
    key = uuid4()
    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(lambda slot: post(client, slot, users[0], key),
                                      [first_slot, second_slot]))
    assert Counter([first.status_code, second.status_code]) == {201: 1, 409: 1}
    loser = first if first.status_code == 409 else second
    assert loser.json()["code"] == "IDEMPOTENCY_KEY_REUSED"
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(Booking)) == 1


def test_concurrent_retry_same_key_and_same_slot(booking_app):
    client, sessions = booking_app
    slot_id, users = slot_and_users(sessions)
    key = uuid4()
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: post(client, slot_id, users[0], key), range(2)))
    assert Counter(response.status_code for response in responses) == {201: 1, 200: 1}
    assert responses[0].json() == responses[1].json()
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(Booking)) == 1
