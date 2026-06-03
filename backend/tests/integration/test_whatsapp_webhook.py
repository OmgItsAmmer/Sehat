"""Integration tests for the Green API webhook receiver."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


@patch("app.services.pipeline.whatsapp.send_text", return_value=True)
@patch("app.agent.nodes.slack.send_triage_alert", return_value=True)
def test_webhook_accepts_incoming_message(
    _mock_slack,
    _mock_send,
    client: TestClient,
    green_api_text_payload: dict,
) -> None:
    response = client.post("/api/whatsapp/webhook", json=green_api_text_payload)
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_webhook_accepts_non_message_events(client: TestClient) -> None:
    payload = {"typeWebhook": "stateInstanceChanged", "stateInstance": "authorized"}
    response = client.post("/api/whatsapp/webhook", json=payload)
    assert response.status_code == 200
    assert response.json() == {"ok": True}
