import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker


def build_engine(url: str | None = None):
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    value = url or os.environ.get("DATABASE_URL")
    if not value:
        raise RuntimeError("Set DATABASE_URL in backend/.env before starting the backend.")
    parsed = make_url(value)
    if parsed.drivername != "postgresql+psycopg":
        raise ValueError("DATABASE_URL must use postgresql+psycopg (PostgreSQL with psycopg 3).")
    return create_engine(parsed, pool_pre_ping=True, pool_size=5, max_overflow=5,
                         pool_timeout=5, connect_args={"connect_timeout": 3})


def get_db(request: Request):
    """For future sync routes: each request gets a separate session."""
    with request.app.state.sessions() as session:
        yield session


def session_factory(engine):
    return sessionmaker(engine, expire_on_commit=False)
