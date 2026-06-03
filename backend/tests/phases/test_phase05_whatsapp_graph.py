"""Phase 5 — webhook runs graph and sends WhatsApp reply (plan.md scenarios)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from app.agent.triage import TriageResult
from app.services import memory
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.integration, pytest.mark.phase5, pytest.mark.asyncio]


@patch("app.services.pipeline.whatsapp.send_text", return_value=True)
@patch("app.agent.nodes.slack.send_triage_alert", return_value=True)
async def test_scenario_p1_emergency(
    _mock_slack,
    mock_send,
    client: TestClient,
    green_api_text_payload: dict,
) -> None:
    """Plan: seene mein dard → P1, 1122 reply."""
    response = client.post("/api/whatsapp/webhook", json=green_api_text_payload)

    assert response.status_code == 200
    mock_send.assert_called_once()
    assert "1122" in mock_send.call_args.kwargs["message"]
    state = await memory.load("79001234567@c.us")
    assert state["priority"] == "P1"


@patch("app.services.pipeline.whatsapp.send_text", return_value=True)
@patch("app.agent.nodes.classify_message_with_gemini")
async def test_scenario_oos_fee_question(
    mock_classify,
    mock_send,
    client: TestClient,
    green_api_text_payload: dict,
) -> None:
    """Plan: fee kitni hai → OOS redirect."""
    payload = {**green_api_text_payload}
    payload["messageData"]["textMessageData"]["textMessage"] = "fee kitni hai consultation ki"
    mock_classify.return_value = TriageResult(
        priority="OOS", confidence=0.95, reasoning="Fee question."
    )

    response = client.post("/api/whatsapp/webhook", json=payload)

    assert response.status_code == 200
    mock_send.assert_called_once()
    assert "City Medical Center" in mock_send.call_args.kwargs["message"]


@patch("app.services.pipeline.whatsapp.send_text", return_value=True)
@patch("app.agent.nodes.classify_message_with_gemini")
async def test_scenario_p3_slot_question_started(
    mock_classify,
    mock_send,
    client: TestClient,
    green_api_text_payload: dict,
) -> None:
    """Plan: appointment + back pain → slot-filling begins."""
    payload = {**green_api_text_payload}
    payload["messageData"]["textMessageData"]["textMessage"] = "appointment chahiye back pain"
    mock_classify.return_value = TriageResult(
        priority="P3", confidence=0.9, reasoning="Routine appointment."
    )

    response = client.post("/api/whatsapp/webhook", json=payload)

    assert response.status_code == 200
    state = await memory.load("79001234567@c.us")
    assert state["priority"] == "P3"
    assert state.get("pending_slot") == "chief_complaint"
    assert mock_send.call_count == 1
