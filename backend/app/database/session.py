from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def is_db_configured() -> bool:
    return bool(settings.database_url)


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    if _engine is None:
        _engine = create_engine(settings.database_url, pool_pre_ping=True)
        _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    return _engine


def get_sessionmaker() -> sessionmaker[Session]:
    if _SessionLocal is None:
        get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


def get_db() -> Generator[Session | None, None, None]:
    """
    FastAPI dependency.

    Returns None when DATABASE_URL is not configured so Phase 1 tests remain pure.
    """
    if not is_db_configured():
        yield None
        return

    SessionLocal = get_sessionmaker()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
