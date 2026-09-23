"""Every database test gets its own disposable schema, never public tables."""
import os
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import build_engine
from app.models import Base
from app.seed import seed


@pytest.fixture
def connection():
    engine = build_engine(os.environ.get("TEST_DATABASE_URL"))
    schema = "test_slotgrab_" + uuid4().hex
    with engine.connect() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        conn.execute(text(f'SET search_path TO "{schema}"'))
        Base.metadata.create_all(conn)
        conn.commit()
        try:
            yield conn
        finally:
            conn.rollback()
            conn.execute(text('SET search_path TO public'))
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            conn.commit()
    engine.dispose()


@pytest.fixture
def session(connection):
    with Session(connection) as session:
        with session.begin():
            seed(session, date(2026, 9, 25), test_users=2)
        yield session
        session.rollback()
