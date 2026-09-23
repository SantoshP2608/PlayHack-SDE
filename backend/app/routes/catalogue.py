"""Read-only catalogue. Availability is a snapshot, never a reservation."""
from datetime import date as Date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Booking, BookingStatus, Facility, Slot, Sport
from ..schemas import ErrorResponse, FacilityResponse, SlotResponse, SportResponse


def no_cache(response: Response):
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(prefix="/api", tags=["Catalogue"], dependencies=[Depends(no_cache)],
                   responses={503: {"model": ErrorResponse}})
Database = Annotated[Session, Depends(get_db)]
PositiveId = Annotated[int, Query(gt=0, le=9223372036854775807)]


@router.get("/sports", response_model=list[SportResponse])
def list_sports(db: Database):
    """List sports alphabetically, including sports with no facilities yet."""
    return db.scalars(select(Sport).order_by(Sport.name, Sport.id)).all()


@router.get("/facilities", response_model=list[FacilityResponse],
            responses={404: {"model": ErrorResponse}})
def list_facilities(sport_id: PositiveId, db: Database):
    """List active facilities for a sport; an existing empty sport returns []."""
    if db.get(Sport, sport_id) is None:
        raise HTTPException(status_code=404, detail="Sport not found")
    return db.scalars(select(Facility).where(
        Facility.sport_id == sport_id, Facility.is_active.is_(True),
    ).order_by(Facility.location, Facility.name, Facility.id)).all()


@router.get("/slots", response_model=list[SlotResponse],
            responses={404: {"model": ErrorResponse}})
def list_slots(facility_id: PositiveId,
               day: Annotated[Date, Query(alias="date", description="Calendar date in IST (YYYY-MM-DD)")],
               db: Database):
    """Return one day's slots ordered by start time, with current DB availability.

    Inactive facilities and slots already started are UNAVAILABLE. Otherwise a
    confirmed booking makes the slot BOOKED. Cancelled history does not block it.
    All date/time fields are local Asia/Kolkata time. No 12-hour release rule in V1.
    """
    if db.get(Facility, facility_id) is None:
        raise HTTPException(status_code=404, detail="Facility not found")
    confirmed = select(Booking.id).where(
        Booking.slot_id == Slot.id, Booking.status == BookingStatus.CONFIRMED,
    ).exists()
    status = case(
        (or_(Facility.is_active.is_(False),
             Slot.slot_date + Slot.start_time <= func.timezone("Asia/Kolkata", func.statement_timestamp())), "UNAVAILABLE"),
        (confirmed, "BOOKED"),
        else_="AVAILABLE",
    )
    query = select(
        Slot.id, Slot.facility_id, Slot.slot_date.label("date"),
        Slot.start_time, Slot.end_time, status.label("status"),
    ).join(Facility, Facility.id == Slot.facility_id).where(
        Slot.facility_id == facility_id, Slot.slot_date == day,
    ).order_by(Slot.start_time, Slot.id)
    return db.execute(query).mappings().all()
