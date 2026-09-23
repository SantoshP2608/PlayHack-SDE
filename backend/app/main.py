from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .database import build_engine, session_factory
from .routes.catalogue import router as catalogue_router
from .routes.bookings import router as bookings_router


class HealthResponse(BaseModel):
    status: Literal["ok", "error"]
    database: Literal["connected", "unavailable"]


def create_app(database_url: str | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app):
        app.state.engine = build_engine(database_url)
        app.state.sessions = session_factory(app.state.engine)
        try:
            yield
        finally:
            app.state.engine.dispose()

    app = FastAPI(title="SlotGrab API", version="0.1.0", lifespan=lifespan)
    app.include_router(catalogue_router)
    app.include_router(bookings_router)

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError):
        # Never expose connection strings, SQL statements or driver errors.
        return JSONResponse(status_code=503,
                            content={"detail": "Database temporarily unavailable"},
                            headers={"Cache-Control": "no-store"})

    @app.get("/health", response_model=HealthResponse,
             responses={503: {"model": HealthResponse}})
    def health(request: Request):
        try:
            with request.app.state.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return JSONResponse(status_code=503, content={"status": "error", "database": "unavailable"})
        return {"status": "ok", "database": "connected"}

    return app


app = create_app()
