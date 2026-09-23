"""Real PostgreSQL tests in isolated, automatically cleaned test schemas."""
import os
from datetime import date, datetime, time, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.main import create_app
from app.models import Base, Booking, BookingStatus, Facility, Slot, Sport, User
from app.seed import seed


def ids(session):
    return session.scalar(select(Slot.id).order_by(Slot.id)), session.scalar(select(User.id).order_by(User.id))


def test_seed_is_repeatable_and_preserves_data(session):
    slot_id, user_id = ids(session)
    session.add(Booking(slot_id=slot_id, user_id=user_id, idempotency_key="keep"))
    session.commit()
    seed(session, date(2026, 9, 25), test_users=2)
    session.commit()
    counts = [session.scalar(select(func.count()).select_from(model)) for model in (Sport, Facility, Slot, User, Booking)]
    assert counts == [3, 11, 110, 2, 1]


def test_one_confirmed_booking_and_rebooking_after_cancel(session):
    slot_id, user_id = ids(session)
    first = Booking(slot_id=slot_id, user_id=user_id, idempotency_key="first")
    session.add(first)
    session.commit()
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.add(Booking(slot_id=slot_id, user_id=user_id, idempotency_key="second"))
            session.flush()
    first.status = BookingStatus.CANCELLED
    first.cancelled_at = datetime.now(timezone.utc)
    session.commit()
    session.add(Booking(slot_id=slot_id, user_id=user_id, idempotency_key="third"))
    session.commit()
    assert session.scalar(select(func.count()).select_from(Booking)) == 2


@pytest.mark.parametrize("values", [
    {"name": " ", "email": "test@iitg.ac.in"},
    {"name": "Test", "email": "test@example.com"},
    {"name": "Test", "email": "test@iitg.ac.in", "study_year": 0},
    {"name": "Test", "email": "SLOTGRAB-DEMO-001@iitg.ac.in"},
])
def test_invalid_users_rejected(session, values):
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.add(User(**values))
            session.flush()


@pytest.mark.parametrize("start,end", [(time(16, 30), time(17, 30)), (time(16), time(18)), (time(19), time(18)), (time(23), time(0))])
def test_invalid_slots_rejected(session, start, end):
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.add(Slot(facility_id=session.scalar(select(Facility.id).limit(1)), slot_date=date(2026, 10, 1), start_time=start, end_time=end))
            session.flush()


def test_foreign_key_and_cancellation_constraints(session):
    slot_id, user_id = ids(session)
    for values in [
        dict(slot_id=999999, user_id=user_id),
        dict(slot_id=slot_id, user_id=999999),
        dict(slot_id=slot_id, user_id=user_id, status=BookingStatus.CANCELLED),
        dict(slot_id=slot_id, user_id=user_id, cancelled_at=datetime.now(timezone.utc)),
    ]:
        with pytest.raises(IntegrityError):
            with session.begin_nested():
                session.add(Booking(**values, idempotency_key=uuid4().hex))
                session.flush()


def test_idempotency_key_unique_across_slots(session):
    slot_ids = list(session.scalars(select(Slot.id).limit(2)))
    user_id = session.scalar(select(User.id).limit(1))
    session.add(Booking(slot_id=slot_ids[0], user_id=user_id, idempotency_key="same"))
    session.commit()
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.add(Booking(slot_id=slot_ids[1], user_id=user_id, idempotency_key="same"))
            session.flush()


def test_duplicate_slot_and_parent_deletion_rejected(session):
    existing = session.scalars(select(Slot).limit(1)).one()
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.add(Slot(facility_id=existing.facility_id, slot_date=existing.slot_date,
                             start_time=existing.start_time, end_time=existing.end_time))
            session.flush()
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.delete(session.get(Facility, existing.facility_id))
            session.flush()


def test_schema_initialization_is_repeatable(connection):
    Base.metadata.create_all(connection)
    connection.commit()
    assert connection.scalar(text("SELECT count(*) FROM information_schema.tables WHERE table_schema = current_schema()")) == 5


def test_health_and_docs():
    with TestClient(create_app(os.environ.get("TEST_DATABASE_URL"))) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "database": "connected"}
        assert client.get("/docs").status_code == 200
        assert "/health" in client.get("/openapi.json").json()["paths"]


def test_unavailable_database_does_not_leak_details():
    with TestClient(create_app("postgresql+psycopg://invalid:secret@127.0.0.1:1/missing")) as client:
        response = client.get("/health")
        assert response.status_code == 503
        assert response.json() == {"status": "error", "database": "unavailable"}
