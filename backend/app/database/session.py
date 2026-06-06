from __future__ import annotations

import logging
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None
_db_available: bool | None = None


def is_db_configured() -> bool:
    return bool(settings.database_url.strip())


def normalize_database_url(url: str) -> str:
    """Use psycopg v3 driver (project installs psycopg[binary], not psycopg2)."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if not is_db_configured():
        raise RuntimeError("DATABASE_URL is not configured")
    if _engine is None:
        url = normalize_database_url(settings.database_url.strip())
        _engine = create_engine(url, pool_pre_ping=True)
        _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    return _engine


def get_sessionmaker() -> sessionmaker[Session]:
    if _SessionLocal is None:
        get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


def db_is_available() -> bool:
    """Whether Postgres is configured and the engine could be created."""
    global _db_available
    if _db_available is not None:
        return _db_available
    if not is_db_configured():
        _db_available = False
        return False
    try:
        get_engine()
        _db_available = True
    except Exception:
        logger.exception("DATABASE_URL is set but Postgres is unavailable")
        _db_available = False
    return _db_available


def rollback_db(db: Session | None) -> None:
    """Reset a failed transaction so later ORM calls on the same request can proceed."""
    if db is None:
        return
    try:
        db.rollback()
    except Exception:
        logger.exception("db rollback failed")


def get_db() -> Generator[Session | None, None, None]:
    """
    FastAPI dependency.

    Returns None when DATABASE_URL is missing or the database cannot be reached.
    """
    if not db_is_available():
        yield None
        return

    SessionLocal = get_sessionmaker()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
