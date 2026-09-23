"""Public catalogue responses; database audit and user fields are not exposed."""
from datetime import date as Date, time as Time
from typing import Literal

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
