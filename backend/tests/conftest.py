"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from app.config import settings
from app.main import app
from app.services import memory
from fastapi.testclient import TestClient


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
