"""Unit-test fixtures (SQLite in-memory DB for Phase 2 persistence tests)."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from app.database.base import Base
from app.models import message, patient  # noqa: F401
from sqlalchemy import create_engine, event
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker


@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(type_, compiler, **kw):  # noqa: ARG001
    return "CHAR(36)"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):  # noqa: ARG001
    return "JSON"


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):  # noqa: ARG001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()
