"""Public catalogue responses; database audit and user fields are not exposed."""
from datetime import date as Date, time as Time
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None


class FacilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sport_id: int
    name: str
    location: str
    is_active: bool


class SlotResponse(BaseModel):
    id: int
    facility_id: int
    date: Date
    start_time: Time
    end_time: Time
    status: Literal["AVAILABLE", "BOOKED", "UNAVAILABLE"]


class ErrorResponse(BaseModel):
    detail: str


class BookingCreate(BaseModel):
    slot_id: int
    idempotency_key: UUID


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slot_id: int
    status: Literal["CONFIRMED", "CANCELLED"]
    created_at: datetime


class BookingErrorResponse(BaseModel):
    code: str
    message: str


class DemoUserResponse(BaseModel):
    id: int
    name: str
