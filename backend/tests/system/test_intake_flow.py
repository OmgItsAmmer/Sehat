"""System tests: full intake path through the running application."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.system


@patch("app.services.pipeline.whatsapp.send_text", return_value=True)
@patch("app.agent.nodes.slack.send_triage_alert", return_value=True)
def test_patient_message_intake_flow(
    _mock_slack,
    _mock_send,
    client: TestClient,
    green_api_text_payload: dict,
) -> None:
    """Health check → WhatsApp webhook → ack mirrors production smoke test."""
    health = client.get("/health")
    assert health.status_code == 200

    webhook = client.post("/api/whatsapp/webhook", json=green_api_text_payload)
    assert webhook.status_code == 200
    assert webhook.json() == {"ok": True}

    # Non-message webhooks must not break the queue (Green API expects 200).
    status_event = client.post(
        "/api/whatsapp/webhook",
        json={"typeWebhook": "stateInstanceChanged", "stateInstance": "authorized"},
    )
    assert status_event.status_code == 200

    # API remains healthy after webhook traffic.
    assert client.get("/health").json() == {"status": "ok"}
