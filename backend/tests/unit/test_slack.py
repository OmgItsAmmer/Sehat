"""Unit tests for Slack triage alerts."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest
from app.services import slack

pytestmark = pytest.mark.unit


@patch("app.services.slack.settings.slack_webhook_url", "https://hooks.slack.com/test")
@patch("httpx.Client")
def test_send_triage_alert_posts_to_webhook(mock_client_cls: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_client_cls.return_value.__enter__.return_value.post.return_value = mock_response

    ok = slack.send_triage_alert(
        patient_phone="79001234567@c.us",
        priority="P1",
        routed_to="cardiology",
        reasoning="Chest pain",
        message_preview="seene mein dard",
        escalated=True,
    )

    assert ok is True
    call = mock_client_cls.return_value.__enter__.return_value.post.call_args
    assert call.args[0] == "https://hooks.slack.com/test"
    assert "P1" in call.kwargs["json"]["text"]
    assert "seene mein dard" in call.kwargs["json"]["text"]


@patch("app.services.slack.settings.slack_webhook_url", "")
def test_send_triage_alert_noop_without_webhook() -> None:
    ok = slack.send_triage_alert(
        patient_phone="x",
        priority="P1",
        routed_to=None,
        reasoning="",
        message_preview="",
        escalated=True,
    )
    assert ok is False


@patch("app.services.slack.settings.slack_webhook_url", "https://hooks.slack.com/test")
@patch("httpx.Client")
def test_send_triage_alert_returns_false_on_http_error(mock_client_cls: MagicMock) -> None:
    mock_client_cls.return_value.__enter__.return_value.post.side_effect = httpx.HTTPError(
        "fail"
    )

    ok = slack.send_triage_alert(
        patient_phone="x",
        priority="P1",
        routed_to=None,
        reasoning="",
        message_preview="",
        escalated=True,
    )
    assert ok is False
