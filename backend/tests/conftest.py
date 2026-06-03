"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from app.config import settings
from app.main import app
from app.services import memory
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _no_live_api_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Never use repo .env credentials in pytest (avoids OpenAI/Green API charges).

    Tests that exercise LLM or outbound HTTP must mock the client or set a fake key
    locally via a test fixture (e.g. openai_api_key + @patch('openai.OpenAI')).
    """
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "openai_model", "gpt-4o-mini")
    monkeypatch.setattr(settings, "green_api_instance", "")
    monkeypatch.setattr(settings, "green_api_token", "")
    monkeypatch.setattr(settings, "slack_webhook_url", "")
    monkeypatch.setattr(settings, "database_url", "")
    monkeypatch.setattr(settings, "redis_url", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    import app.database.session as db_session_module

    monkeypatch.setattr(db_session_module, "_db_available", None)
    monkeypatch.setattr(db_session_module, "_engine", None)
    monkeypatch.setattr(db_session_module, "_SessionLocal", None)


@pytest.fixture(autouse=True)
async def _in_memory_sessions_for_http_tests(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncGenerator[None, None]:
    """Integration/system tests use in-memory sessions (no live Redis)."""
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


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def green_api_text_payload() -> dict:
    """Minimal Green API incoming text message (from runbook curl example)."""
    return {
        "typeWebhook": "incomingMessageReceived",
        "instanceData": {
            "idInstance": 1,
            "wid": "0@c.us",
            "typeInstance": "whatsapp",
        },
        "timestamp": 1700000000,
        "idMessage": "TEST",
        "senderData": {
            "chatId": "79001234567@c.us",
            "sender": "79001234567@c.us",
            "chatName": "Test",
            "senderName": "Test",
        },
        "messageData": {
            "typeMessage": "textMessage",
            "textMessageData": {"textMessage": "seene mein dard"},
        },
    }
