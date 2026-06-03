"""Unit tests for webhook intake orchestration."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from app.agent.triage import TriageResult
from app.services import intake

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@patch("app.services.pipeline.whatsapp.send_text", return_value=True)
@patch("app.agent.nodes.slack.send_triage_alert", return_value=True)
async def test_p1_message_triggers_slack_and_reply(_mock_slack, _mock_send) -> None:
    result = await intake.process_incoming_message(
        chat_id="79001234567@c.us",
        body="seene mein dard",
    )

    assert result["priority"] == "P1"
    assert result["escalated"] is True
    _mock_slack.assert_called_once()
    _mock_send.assert_called_once()
    assert "1122" in _mock_send.call_args.kwargs["message"]


@patch("app.services.pipeline.whatsapp.send_text", return_value=True)
@patch("app.agent.nodes.classify_message_with_openai")
async def test_oos_message_sends_redirect_without_slack(
    mock_classify,
    _mock_send,
) -> None:
    mock_classify.return_value = TriageResult(
        priority="OOS",
        confidence=0.95,
        reasoning="Billing.",
    )

    result = await intake.process_incoming_message(
        chat_id="79001234567@c.us",
        body="fee kitni hai",
    )

    assert result["priority"] == "OOS"
    assert "City Medical Center" in result["reply"]
    _mock_send.assert_called_once()


@patch("app.services.pipeline.whatsapp.send_text", return_value=True)
@patch("app.agent.nodes.classify_message_with_openai")
async def test_p3_slot_flow_across_two_messages(mock_classify, mock_send) -> None:
    mock_classify.return_value = TriageResult(
        priority="P3",
        confidence=0.9,
        reasoning="Routine appointment.",
    )
    chat = "79001234567@c.us"

    first = await intake.process_incoming_message(
        chat_id=chat,
        body="appointment chahiye back pain",
    )
    assert first["priority"] == "P3"
    assert first.get("pending_slot") == "chief_complaint"
    assert first["reply"]
    assert not first["slots_complete"]

    mock_classify.reset_mock()
    second = await intake.process_incoming_message(chat_id=chat, body="lower back, one week")
    assert second["slots"].get("chief_complaint") == "lower back, one week"
    assert second.get("pending_slot") in ("symptom_duration", None)
    assert mock_send.call_count == 2
