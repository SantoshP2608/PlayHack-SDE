"""Atomic V1 booking; demo identity is deliberately local and opt-in."""
import os
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Booking, BookingStatus, Facility, Slot, User
from ..schemas import BookingCreate, BookingErrorResponse, BookingResponse, DemoUserResponse


router = APIRouter(prefix="/api", tags=["Bookings"],
                   responses={401: {"model": BookingErrorResponse},
                              403: {"model": BookingErrorResponse},
                              404: {"model": BookingErrorResponse},
                              409: {"model": BookingErrorResponse}})
Database = Annotated[Session, Depends(get_db)]


def error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"code": code, "message": message},
                        headers={"Cache-Control": "no-store"})


def result(booking: Booking, status: int) -> JSONResponse:
    payload = BookingResponse.model_validate(booking).model_dump(mode="json")
    return JSONResponse(status_code=status, content=payload,
                        headers={"Cache-Control": "no-store"})


def existing_key_result(existing: Booking, requested_slot: int) -> JSONResponse:
    if existing.slot_id != requested_slot:
        return error(409, "IDEMPOTENCY_KEY_REUSED", "This request key was used for another slot.")
    if existing.status == BookingStatus.CANCELLED:
        return error(409, "REQUEST_ALREADY_CANCELLED", "The original booking was cancelled; use a new request key.")
    return result(existing, 200)


def demo_allowed(request: Request) -> bool:
    return (os.environ.get("SLOTGRAB_DEMO_MODE") == "1"
            and request.client is not None
            and request.client.host in {"127.0.0.1", "::1", "testclient"})


@router.get("/demo/users", response_model=list[DemoUserResponse])
def list_demo_users(request: Request, db: Database):
    """Expose only seed identities for the local, opt-in demo."""
    if not demo_allowed(request):
        return error(403, "DEMO_DISABLED", "Local demo booking mode is disabled.")
    users = db.execute(select(User.id, User.name).where(
        User.name.like("Synthetic Demo User %"),
        User.email.like("slotgrab-demo-%@iitg.ac.in"),
    ).order_by(User.id)).mappings().all()
    return JSONResponse(content=[dict(row) for row in users],
                        headers={"Cache-Control": "no-store"})


@router.post("/bookings", response_model=BookingResponse, status_code=201,
             responses={200: {"model": BookingResponse}})
def create_booking(body: BookingCreate, request: Request, db: Database,
                   demo_user_id: Annotated[int | None, Header(alias="X-Demo-User-Id", gt=0,
                                                              le=9223372036854775807)] = None):
    # Header identity is not authentication. It is only accepted by an explicitly
    # enabled local demo server. Production must replace this dependency with auth.
    if not demo_allowed(request):
        return error(403, "DEMO_DISABLED", "Local demo booking mode is disabled.")
    if demo_user_id is None:
        return error(401, "DEMO_USER_REQUIRED", "Provide a demo user ID in X-Demo-User-Id.")
    if body.slot_id <= 0 or body.slot_id > 9223372036854775807:
        return error(422, "INVALID_SLOT", "slot_id must be a positive PostgreSQL bigint.")

    key = str(body.idempotency_key)
    try:
        with db.begin():
            if db.get(User, demo_user_id) is None:
                return error(401, "UNKNOWN_DEMO_USER", "Demo user not found.")
            prior = db.scalar(select(Booking).where(
                Booking.user_id == demo_user_id, Booking.idempotency_key == key,
            ))
            if prior is not None:
                return existing_key_result(prior, body.slot_id)

            # Blocking lock, never SKIP LOCKED. All callers for this slot wait
            # their turn and inspect the committed winner before deciding.
            locked = db.execute(select(Slot, Facility.is_active).join(
                Facility, Facility.id == Slot.facility_id,
            ).where(Slot.id == body.slot_id).with_for_update(of=(Slot, Facility))).first()
            if locked is None:
                return error(404, "SLOT_NOT_FOUND", "Slot not found.")
            slot, is_active = locked
            # A retry may have waited for this lock; check the key again.
            prior = db.scalar(select(Booking).where(
                Booking.user_id == demo_user_id, Booking.idempotency_key == key,
            ))
            if prior is not None:
                return existing_key_result(prior, body.slot_id)
            now_ist = db.scalar(select(func.timezone("Asia/Kolkata", func.statement_timestamp())))
            if not is_active or (slot.slot_date, slot.start_time) <= (now_ist.date(), now_ist.time()):
                return error(409, "SLOT_UNAVAILABLE", "This slot cannot be booked.")
            taken = db.scalar(select(Booking.id).where(
                Booking.slot_id == slot.id, Booking.status == BookingStatus.CONFIRMED,
            ))
            if taken is not None:
                return error(409, "SLOT_ALREADY_BOOKED", "Another user booked this slot first.")
            booking = Booking(slot_id=slot.id, user_id=demo_user_id, idempotency_key=key)
            db.add(booking)
            db.flush()
            created = result(booking, 201)
        return created
    except IntegrityError:
        # Unique indexes are the final protection if concurrent requests use
        # the same key on different slots, or another writer omits this lock.
        db.rollback()
        prior = db.scalar(select(Booking).where(
            Booking.user_id == demo_user_id, Booking.idempotency_key == key,
        ))
        if prior is not None:
            return existing_key_result(prior, body.slot_id)
        return error(409, "SLOT_ALREADY_BOOKED", "Another user booked this slot first.")
