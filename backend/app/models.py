"""Approved V1 schema. PostgreSQL is required; all slot wall times are IST."""
from datetime import date, datetime, time
from enum import Enum as PythonEnum

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Date, DateTime, Enum, ForeignKey,
    Identity, Index, SmallInteger, String, Text, Time, UniqueConstraint, func, text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254))
    roll_number: Mapped[str | None] = mapped_column(String(32), unique=True)
    department: Mapped[str | None] = mapped_column(String(100))
    study_year: Mapped[int | None] = mapped_column(SmallInteger)
    __table_args__ = (
        CheckConstraint("btrim(name) <> ''", name="users_name_not_blank"),
        CheckConstraint(r"lower(email) ~ '^[^@[:space:]]+@iitg\.ac\.in$'", name="users_iitg_email"),
        CheckConstraint("study_year IS NULL OR study_year > 0", name="users_study_year_positive"),
        Index("users_email_unique_ci", func.lower(email), unique=True),
    )


class Sport(TimestampMixin, Base):
    __tablename__ = "sports"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        CheckConstraint("btrim(name) <> ''", name="sports_name_not_blank"),
        Index("sports_name_unique_ci", func.lower(name), unique=True),
    )


class Facility(TimestampMixin, Base):
    __tablename__ = "facilities"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    sport_id: Mapped[int] = mapped_column(ForeignKey("sports.id", ondelete="RESTRICT"))
    name: Mapped[str] = mapped_column(String(100))
    location: Mapped[str] = mapped_column(String(150))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    __table_args__ = (
        CheckConstraint("btrim(name) <> ''", name="facilities_name_not_blank"),
        CheckConstraint("btrim(location) <> ''", name="facilities_location_not_blank"),
        UniqueConstraint("sport_id", "location", "name", name="facilities_identity_unique"),
        Index("facilities_sport_active_idx", "sport_id", "is_active"),
    )


class Slot(TimestampMixin, Base):
    __tablename__ = "slots"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"))
    slot_date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    __table_args__ = (
        CheckConstraint("end_time > start_time", name="slots_valid_time_range"),
        CheckConstraint("end_time = start_time + INTERVAL '1 hour'", name="slots_one_hour_duration"),
        CheckConstraint("EXTRACT(MINUTE FROM start_time) = 0 AND EXTRACT(SECOND FROM start_time) = 0", name="slots_start_on_full_hour"),
        UniqueConstraint("facility_id", "slot_date", "start_time", name="slots_resource_time_unique"),
        Index("slots_date_lookup_idx", "slot_date", "facility_id", "start_time"),
    )


class BookingStatus(str, PythonEnum):
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class Booking(TimestampMixin, Base):
    __tablename__ = "bookings"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    slot_id: Mapped[int] = mapped_column(ForeignKey("slots.id", ondelete="RESTRICT"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    status: Mapped[BookingStatus] = mapped_column(Enum(BookingStatus, name="booking_status"), server_default="CONFIRMED")
    idempotency_key: Mapped[str] = mapped_column(String(128))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="bookings_idempotency_unique"),
        CheckConstraint("btrim(idempotency_key) <> ''", name="bookings_key_not_blank"),
        CheckConstraint("(status = 'CONFIRMED' AND cancelled_at IS NULL) OR (status = 'CANCELLED' AND cancelled_at IS NOT NULL)", name="bookings_cancellation_consistent"),
        CheckConstraint("cancelled_at IS NULL OR cancelled_at >= created_at", name="bookings_cancellation_after_creation"),
        Index("one_confirmed_booking_per_slot", "slot_id", unique=True, postgresql_where=text("status = 'CONFIRMED'")),
        Index("bookings_user_status_idx", "user_id", "status", text("created_at DESC")),
    )
