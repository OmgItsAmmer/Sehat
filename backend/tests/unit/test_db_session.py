"""Phase 2 unit tests: database session dependency."""

from __future__ import annotations

import pytest
from app.database.session import get_db, get_engine, is_db_configured

pytestmark = pytest.mark.unit


def test_is_db_configured_false_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.database.session.settings.database_url", "")
    assert is_db_configured() is False


def test_is_db_configured_true_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.database.session.settings.database_url",
        "postgresql://user:pass@localhost/db",
    )
    assert is_db_configured() is True


def test_get_db_yields_none_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.database.session.settings.database_url", "")
    db_gen = get_db()
    assert next(db_gen) is None


def test_get_engine_raises_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.database.session as session_module

    monkeypatch.setattr(session_module, "_engine", None)
    monkeypatch.setattr(session_module, "_SessionLocal", None)
    monkeypatch.setattr("app.database.session.settings.database_url", "")

    with pytest.raises(RuntimeError, match="DATABASE_URL is not configured"):
        get_engine()
