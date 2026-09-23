"""Create missing V1 tables. This is initial setup, not a migration mechanism."""
from .database import build_engine
from .models import Base


def main():
    engine = build_engine()
    try:
        with engine.begin() as connection:
            Base.metadata.create_all(connection)
        print("V1 tables ready. Existing tables and records preserved.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
