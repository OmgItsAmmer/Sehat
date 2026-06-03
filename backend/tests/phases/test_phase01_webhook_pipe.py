"""Phase 1 — Green API webhook receives messages and returns 200."""

from __future__ import annotations

import pytest
from app.api.whatsapp import _extract_message_body, _format_incoming_log
from app.main import app
from fastapi.routing import APIRoute

pytestmark = [pytest.mark.unit, pytest.mark.phase1]


def test_whatsapp_webhook_route_registered() -> None:
    paths = {
        route.path
        for route in app.routes
        if isinstance(route, APIRoute)
    }
    assert "/api/whatsapp/webhook" in paths


@pytest.mark.parametrize(
    "message_data",
    [
        {
            "typeMessage": "textMessage",
            "textMessageData": {"textMessage": "seene mein dard"},
        },
    ],
)
def test_extract_text_message_body(message_data: dict) -> None:
    assert _extract_message_body(message_data) == "seene mein dard"


def test_incoming_log_block_contains_chat_and_body() -> None:
    payload = {
        "typeWebhook": "incomingMessageReceived",
        "senderData": {"chatId": "79001234567@c.us", "senderName": "Test"},
        "messageData": {
            "typeMessage": "textMessage",
            "textMessageData": {"textMessage": "hello"},
        },
    }
    block = _format_incoming_log(payload)
    assert "79001234567@c.us" in block
    assert "hello" in block
