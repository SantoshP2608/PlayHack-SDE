"""Run the judge-facing 50-request booking race against a live local API."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import threading
from time import perf_counter
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .database import build_engine
from .models import Booking, BookingStatus, Facility, Slot


@dataclass(frozen=True)
class Outcome:
    status_code: int | None
    error_code: str | None = None
    transport_error: str | None = None


@dataclass(frozen=True)
class RaceSummary:
    requests: int
    confirmed_responses: int
    conflict_responses: int
    unexpected_responses: int
    database_confirmed: int
    elapsed_seconds: float

    @property
    def oversold(self) -> int:
        return max(0, self.database_confirmed - 1)

    @property
    def passed(self) -> bool:
        return (
            self.confirmed_responses == 1
            and self.conflict_responses == self.requests - 1
            and self.unexpected_responses == 0
            and self.database_confirmed == 1
        )


def summarize(outcomes: list[Outcome], database_confirmed: int, elapsed: float) -> RaceSummary:
    confirmed = sum(item.status_code == 201 for item in outcomes)
    conflicts = sum(
        item.status_code == 409 and item.error_code == "SLOT_ALREADY_BOOKED"
        for item in outcomes
    )
    return RaceSummary(
        requests=len(outcomes),
        confirmed_responses=confirmed,
        conflict_responses=conflicts,
        unexpected_responses=len(outcomes) - confirmed - conflicts,
        database_confirmed=database_confirmed,
        elapsed_seconds=elapsed,
    )


def require_local_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {
        "127.0.0.1", "localhost", "::1"
    }:
        raise ValueError("--base-url must point to a local SlotGrab API.")
    return base_url.rstrip("/")


def find_available_slot(engine, requested_slot_id: int | None) -> Slot:
    now_ist = func.timezone("Asia/Kolkata", func.statement_timestamp())
    confirmed_exists = select(Booking.id).where(
        Booking.slot_id == Slot.id,
        Booking.status == BookingStatus.CONFIRMED,
    ).exists()
    statement = (
        select(Slot)
        .join(Facility, Facility.id == Slot.facility_id)
        .where(
            Facility.is_active.is_(True),
            ~confirmed_exists,
            Slot.slot_date + Slot.start_time > now_ist,
        )
        .order_by(Slot.slot_date, Slot.start_time, Slot.id)
    )
    if requested_slot_id is not None:
        statement = statement.where(Slot.id == requested_slot_id)
    with Session(engine) as session:
        slot = session.scalar(statement.limit(1))
    if slot is None:
        target = f"slot {requested_slot_id}" if requested_slot_id else "a future free slot"
        raise RuntimeError(
            f"Could not find {target}. Seed a future date or choose another --slot-id."
        )
    return slot


def load_demo_users(base_url: str, request_count: int) -> list[int]:
    response = httpx.get(f"{base_url}/api/demo/users", timeout=10)
    response.raise_for_status()
    users = [int(item["id"]) for item in response.json()]
    if len(users) < request_count:
        raise RuntimeError(
            f"The API returned {len(users)} demo users; {request_count} are required. "
            "Seed with --test-users 50 and restart with SLOTGRAB_DEMO_MODE=1."
        )
    return users[:request_count]


def fire_race(base_url: str, slot_id: int, user_ids: list[int]) -> tuple[list[Outcome], float]:
    start_gate = threading.Barrier(len(user_ids) + 1)

    def book(user_id: int) -> Outcome:
        start_gate.wait()
        try:
            response = httpx.post(
                f"{base_url}/api/bookings",
                headers={"X-Demo-User-Id": str(user_id)},
                json={"slot_id": slot_id, "idempotency_key": str(uuid4())},
                timeout=60,
            )
            error_code = None
            if response.status_code != 201:
                try:
                    error_code = response.json().get("code")
                except (ValueError, AttributeError):
                    error_code = None
            return Outcome(response.status_code, error_code)
        except httpx.HTTPError as exc:
            return Outcome(None, transport_error=f"{type(exc).__name__}: {exc}")

    started = perf_counter()
    with ThreadPoolExecutor(max_workers=len(user_ids)) as pool:
        futures = [pool.submit(book, user_id) for user_id in user_ids]
        start_gate.wait()
        outcomes = [future.result() for future in futures]
    return outcomes, perf_counter() - started


def confirmed_count(engine, slot_id: int) -> int:
    with engine.connect() as connection:
        return int(connection.scalar(select(func.count()).select_from(Booking).where(
            Booking.slot_id == slot_id,
            Booking.status == BookingStatus.CONFIRMED,
        )) or 0)


def print_report(slot: Slot, summary: RaceSummary, outcomes: list[Outcome]) -> None:
    print("\nSLOTGRAB CONCURRENCY PROOF")
    print(f"Slot: {slot.id} | {slot.slot_date} | {slot.start_time}-{slot.end_time}")
    print(f"Requests fired:       {summary.requests}")
    print(f"Bookings confirmed:   {summary.confirmed_responses}")
    print(f"Clean conflicts:      {summary.conflict_responses}")
    print(f"Unexpected responses: {summary.unexpected_responses}")
    print(f"Database confirmed:   {summary.database_confirmed}")
    print(f"Oversold:             {summary.oversold}")
    print(f"Elapsed:              {summary.elapsed_seconds:.2f}s")
    print(f"RESULT:               {'PASS' if summary.passed else 'FAIL'}")
    if not summary.passed:
        details: dict[str, int] = {}
        for item in outcomes:
            key = item.transport_error or f"HTTP {item.status_code} {item.error_code or ''}".rstrip()
            details[key] = details.get(key, 0) + 1
        print(f"Unexpected detail:    {details}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fire simultaneous bookings at one free slot and verify PostgreSQL."
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--slot-id", type=int, help="Optional known free future slot ID")
    parser.add_argument("--requests", type=int, default=50, choices=range(2, 51), metavar="2..50")
    args = parser.parse_args()

    try:
        base_url = require_local_url(args.base_url)
        engine = build_engine()
        try:
            slot = find_available_slot(engine, args.slot_id)
            user_ids = load_demo_users(base_url, args.requests)
            outcomes, elapsed = fire_race(base_url, slot.id, user_ids)
            summary = summarize(outcomes, confirmed_count(engine, slot.id), elapsed)
            print_report(slot, summary, outcomes)
            return 0 if summary.passed else 1
        finally:
            engine.dispose()
    except (ValueError, RuntimeError, httpx.HTTPError, SQLAlchemyError) as exc:
        print(f"Race demo could not run: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
