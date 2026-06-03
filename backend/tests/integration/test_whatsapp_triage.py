"""Integration tests: webhook runs triage graph and sends WhatsApp reply."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from app.services import memory
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@patch("app.services.pipeline.whatsapp.send_text", return_value=True)
@patch("app.agent.nodes.slack.send_triage_alert", return_value=True)
async def test_webhook_p1_runs_graph_and_replies(
    _mock_slack,
    mock_send,
    client: TestClient,
    green_api_text_payload: dict,
) -> None:
    response = client.post("/api/whatsapp/webhook", json=green_api_text_payload)

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    mock_send.assert_called_once()
    assert "1122" in mock_send.call_args.kwargs["message"]

    state = await memory.load("79001234567@c.us")
    assert state["priority"] == "P1"


@patch("app.services.pipeline.whatsapp.send_text", return_value=True)
@patch("app.agent.nodes.classify_message_with_openai")
async def test_webhook_oos_scenario(
    mock_classify,
    mock_send,
    client: TestClient,
    green_api_text_payload: dict,
) -> None:
    from app.agent.triage import TriageResult

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
async def test_webhook_non_message_still_ok(mock_send, client: TestClient) -> None:
    payload = {"typeWebhook": "stateInstanceChanged", "stateInstance": "authorized"}
    response = client.post("/api/whatsapp/webhook", json=payload)
    assert response.status_code == 200
    mock_send.assert_not_called()
