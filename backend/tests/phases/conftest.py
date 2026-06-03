"""Shared fixtures for plan.md phase test suites (1–9)."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator

import pytest
from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.models import message, override, patient  # noqa: F401
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(type_, compiler, **kw):  # noqa: ARG001
    return "CHAR(36)"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):  # noqa: ARG001
    return "JSON"


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

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


@pytest.fixture
def client_with_db(db_session) -> Generator[TestClient, None, None]:
    """TestClient with Postgres dependency replaced by in-memory SQLite."""

    def _override_get_db() -> Generator:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
async def _phase_http_memory(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncGenerator[None, None]:
    """Integration/system phase tests never depend on live Redis."""
    from app.config import settings
    from app.services import memory

    markers = {m.name for m in request.node.iter_markers()}
    if not markers & {"integration", "system"}:
        yield
        return

    monkeypatch.setattr(settings, "redis_url", "")
    await memory.close_redis()
    memory.use_redis_client(None)
    await memory.clear_all()
    yield
    await memory.close_redis()
    memory.use_redis_client(None)
    await memory.clear_all()
