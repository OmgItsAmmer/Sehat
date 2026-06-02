"""Unit tests for Green API message parsing helpers."""

from __future__ import annotations

import pytest
from app.api.whatsapp import _extract_message_body, _format_incoming_log

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("message_data", "expected"),
    [
        (
            {
                "typeMessage": "textMessage",
                "textMessageData": {"textMessage": "Hello Sehat"},
            },
            "Hello Sehat",
        ),
        (
            {
                "typeMessage": "extendedTextMessage",
                "extendedTextMessageData": {"text": "Extended text"},
            },
            "Extended text",
        ),
        (
            {
                "typeMessage": "imageMessage",
                "fileMessageData": {"caption": "Photo caption"},
            },
            "Photo caption",
        ),
        (
            {"typeMessage": "imageMessage", "fileMessageData": {}},
            "[imageMessage]",
        ),
        (
            {
                "typeMessage": "interactiveButtonsReply",
                "interactiveButtonsReply": {"contentText": "Yes"},
            },
            "Yes",
        ),
        ({"typeMessage": "unknownType"}, None),
    ],
)
def test_extract_message_body(message_data: dict, expected: str | None) -> None:
    assert _extract_message_body(message_data) == expected


def test_format_incoming_log_includes_sender_and_message() -> None:
    payload = {
        "typeWebhook": "incomingMessageReceived",
        "senderData": {
            "chatId": "79001234567@c.us",
            "senderName": "Test",
        },
        "messageData": {
            "typeMessage": "textMessage",
            "textMessageData": {"textMessage": "seene mein dard"},
        },
    }
    block = _format_incoming_log(payload)
    assert "incomingMessageReceived" in block
    assert "79001234567@c.us" in block
    assert "seene mein dard" in block
