"""Shared pytest fixtures."""

from __future__ import annotations

import pytest
from app.main import app
from fastapi.testclient import TestClient


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
