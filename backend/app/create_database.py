"""Create only the configured database, using local development credentials."""
from sqlalchemy import create_engine, text
from .database import build_engine


def main():
    target = build_engine()
    name = target.url.database
    if not name or name in {"postgres", "template0", "template1"}:
        raise ValueError("Choose a dedicated application database.")
    admin = create_engine(target.url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as connection:
            exists = connection.scalar(text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": name})
            if not exists:
                quoted = connection.dialect.identifier_preparer.quote_identifier(name)
                connection.execute(text(f"CREATE DATABASE {quoted}"))
        print("Configured application database exists.")
    finally:
        target.dispose()
        admin.dispose()


if __name__ == "__main__":
    main()
