"""Pipeline tests — memory, human review, override resume."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from app.agent.triage import TriageResult
from app.services import memory, pipeline

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@patch("app.services.pipeline.whatsapp.send_text", return_value=True)
@patch("app.agent.nodes.classify_message_with_openai")
async def test_low_confidence_pauses_for_human_review(mock_classify, _mock_send) -> None:
    mock_classify.return_value = TriageResult(
        priority="P3",
        confidence=0.6,
        reasoning="Uncertain routine case.",
    )
    chat = "79001234567@c.us"

    result = await pipeline.process_inbound(chat_id=chat, body="maybe need doctor sometime")

    assert result["priority"] == "P3"
    assert result["awaiting_human_review"] is True
    assert result.get("pending_slot") is None
    _mock_send.assert_called_once()

    stored = await memory.load(chat)
    assert stored["awaiting_human_review"] is True


@patch("app.services.pipeline.whatsapp.send_text", return_value=True)
@patch("app.agent.nodes.classify_message_with_openai")
async def test_while_awaiting_review_patient_gets_hold_message(mock_classify, mock_send) -> None:
    mock_classify.return_value = TriageResult(
        priority="P2",
        confidence=0.5,
        reasoning="Uncertain.",
    )
    chat = "79001234567@c.us"
    await pipeline.process_inbound(chat_id=chat, body="child fever unclear")

    mock_send.reset_mock()
    second = await pipeline.process_inbound(chat_id=chat, body="also cough")

    assert second["awaiting_human_review"] is True
    assert "reception" in (second.get("reply") or "").lower()
    assert mock_send.call_count == 1


@patch("app.services.pipeline.whatsapp.send_text", return_value=True)
@patch("app.agent.nodes.slack.send_triage_alert", return_value=True)
@patch("app.agent.nodes.classify_message_with_openai")
async def test_upgrade_override_resumes_and_replies(
    mock_classify,
    _mock_slack,
    mock_send,
) -> None:
    mock_classify.return_value = TriageResult(
        priority="P3",
        confidence=0.55,
        reasoning="Ambiguous symptoms.",
    )
    chat = "79001234567@c.us"
    await pipeline.process_inbound(chat_id=chat, body="pain maybe serious")

    from app.services.override import apply_override

    out = await apply_override(
        patient_phone=chat,
        action="upgrade",
        receptionist_id="sana",
        db=None,
    )

    assert out["original_priority"] == "P3"
    assert out["priority"] == "P2"
    assert out["status"] == "resumed"
    assert mock_send.call_count >= 2

    stored = await memory.load(chat)
    assert stored.get("awaiting_human_review") is False
    assert stored.get("human_review_resolved") is True
