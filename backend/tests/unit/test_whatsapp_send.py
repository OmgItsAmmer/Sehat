"""Unit tests for Green API outbound send."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest
from app.services import whatsapp

pytestmark = pytest.mark.unit


@patch("app.services.whatsapp.settings.green_api_instance", "123")
@patch("app.services.whatsapp.settings.green_api_token", "token")
@patch("httpx.Client")
def test_send_text_posts_to_green_api(mock_client_cls: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_client_cls.return_value.__enter__.return_value.post.return_value = mock_response

    ok = whatsapp.send_text(chat_id="79001234567@c.us", message="Hello")

    assert ok is True
    call = mock_client_cls.return_value.__enter__.return_value.post.call_args
    assert "waInstance123/sendMessage/token" in call.args[0]
    assert call.kwargs["json"] == {"chatId": "79001234567@c.us", "message": "Hello"}


def test_send_text_skips_when_not_configured() -> None:
    with patch("app.services.whatsapp.settings.green_api_instance", ""):
        ok = whatsapp.send_text(chat_id="79001234567@c.us", message="Hello")
    assert ok is False


def test_send_text_skips_empty_message() -> None:
    assert whatsapp.send_text(chat_id="79001234567@c.us", message="   ") is False


@patch("app.services.whatsapp.settings.green_api_instance", "123")
@patch("app.services.whatsapp.settings.green_api_token", "token")
@patch("httpx.Client")
def test_send_text_returns_false_on_http_error(mock_client_cls: MagicMock) -> None:
    mock_client_cls.return_value.__enter__.return_value.post.side_effect = httpx.HTTPError(
        "fail"
    )
    assert whatsapp.send_text(chat_id="79001234567@c.us", message="Hi") is False
