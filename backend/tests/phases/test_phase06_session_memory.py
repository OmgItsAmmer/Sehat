"""Phase 6 — Redis/in-memory session persists TriageState across messages."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from app.agent.triage import TriageResult
from app.services import intake, memory
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.phase6]


@pytest.mark.unit
async def test_memory_round_trip_preserves_priority() -> None:
    phone = "79001234567@c.us"
    await memory.save(phone, {"patient_phone": phone, "priority": "P3", "messages": ["turn1"]})
    loaded = await memory.load(phone)
    assert loaded["priority"] == "P3"
    assert loaded["messages"] == ["turn1"]


@pytest.mark.integration
@patch("app.services.pipeline.whatsapp.send_text", return_value=True)
@patch("app.agent.nodes.classify_message_with_openai")
def test_second_webhook_resumes_without_reclassify(
    mock_classify,
    _mock_send,
    client: TestClient,
    green_api_text_payload: dict,
) -> None:
    """Turn 2 keeps priority from turn 1 (ingress → slot_check, not classify)."""
    import asyncio

    mock_classify.return_value = TriageResult(priority="P3", confidence=0.9, reasoning="Routine.")
    payload = {**green_api_text_payload}
    payload["messageData"]["textMessageData"]["textMessage"] = "appointment chahiye back pain"

    client.post("/api/whatsapp/webhook", json=payload)
    mock_classify.reset_mock()

    payload["messageData"]["textMessageData"]["textMessage"] = "lower back, one week"
    client.post("/api/whatsapp/webhook", json=payload)

    mock_classify.assert_not_called()
    state = asyncio.run(memory.load("79001234567@c.us"))
    assert state["priority"] == "P3"
    assert state["slots"].get("chief_complaint") == "lower back, one week"


@pytest.mark.integration
@pytest.mark.asyncio
@patch("app.services.pipeline.whatsapp.send_text", return_value=True)
@patch("app.agent.nodes.classify_message_with_openai")
async def test_intake_two_turn_slot_flow(mock_classify, _mock_send) -> None:
    mock_classify.return_value = TriageResult(priority="P3", confidence=0.9, reasoning="Routine.")
    chat = "79009990001@c.us"
    first = await intake.process_incoming_message(
        chat_id=chat, body="appointment chahiye back pain"
    )
    assert first.get("pending_slot") == "chief_complaint"

    mock_classify.reset_mock()
    second = await intake.process_incoming_message(chat_id=chat, body="lower back, one week")
    mock_classify.assert_not_called()
    assert second["slots"].get("chief_complaint") == "lower back, one week"
