"""Repeatable, insert-only demo catalogue. Provenance: backend/README.md."""
import argparse
from datetime import date, time, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from .database import build_engine
from .models import Facility, Slot, Sport, User

SPORTS = ("Badminton", "Tennis", "Football")
# Deck pp. 7-8: six Old SAC and four New SAC badminton courts; New SAC tennis C1.
FACILITIES = [("Badminton", "Old SAC", f"Court {n}") for n in range(1, 7)] + [
    ("Badminton", "New SAC", f"Court {n}") for n in range(1, 5)
] + [("Tennis", "New SAC", "Court 1")]


def seed(session: Session, start_date: date, day_count: int = 2, test_users: int = 0):
    # Caller supplies one transaction, so a failure cannot leave half a seed.
    for name in SPORTS:
        session.execute(insert(Sport).values(name=name).on_conflict_do_nothing())
    sport_ids = dict(session.execute(select(Sport.name, Sport.id)).all())
    for sport, location, name in FACILITIES:
        values = dict(sport_id=sport_ids[sport], location=location, name=name)
        session.execute(insert(Facility).values(**values).on_conflict_do_nothing())
        facility_id = session.scalar(select(Facility.id).filter_by(**values))
        for offset in range(day_count):
            for hour in range(16, 21):
                session.execute(insert(Slot).values(
                    facility_id=facility_id, slot_date=start_date + timedelta(days=offset),
                    start_time=time(hour), end_time=time(hour + 1),
                ).on_conflict_do_nothing())
    # The PDFs do not supply verified email addresses. Synthetic users are opt-in.
    for number in range(1, test_users + 1):
        session.execute(insert(User).values(
            name=f"Synthetic Demo User {number:03}",
            email=f"slotgrab-demo-{number:03}@iitg.ac.in",
        ).on_conflict_do_nothing())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", type=date.fromisoformat, required=True)
    parser.add_argument("--days", type=int, default=2)
    parser.add_argument("--test-users", type=int, default=0)
    args = parser.parse_args()
    if not 1 <= args.days <= 31 or not 0 <= args.test_users <= 1000:
        parser.error("--days must be 1..31; --test-users must be 0..1000")
    engine = build_engine()
    try:
        with Session(engine) as session, session.begin():
            seed(session, args.start_date, args.days, args.test_users)
        print("Demo seed complete; existing records preserved.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
