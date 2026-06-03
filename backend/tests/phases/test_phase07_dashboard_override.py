"""Phase 7 — dashboard APIs and receptionist human override."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from app.agent.triage import TriageResult
from app.models.override import Override
from app.services import memory
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

pytestmark = [pytest.mark.integration, pytest.mark.phase7]


def test_list_cases_includes_active_session(client: TestClient) -> None:
    import asyncio

    asyncio.run(memory.clear_all())
    with (
        patch("app.services.pipeline.whatsapp.send_text", return_value=True),
        patch("app.agent.nodes.slack.send_triage_alert", return_value=True),
    ):
        client.post(
            "/api/whatsapp/webhook",
            json={
                "typeWebhook": "incomingMessageReceived",
                "senderData": {"chatId": "79001234567@c.us", "senderName": "Test"},
                "messageData": {
                    "typeMessage": "textMessage",
                    "textMessageData": {"textMessage": "seene mein dard"},
                },
            },
        )

    response = client.get("/api/cases")
    assert response.status_code == 200
    cases = response.json()["cases"]
    assert any(c["phone"] == "79001234567@c.us" and c["priority"] == "P1" for c in cases)


def test_override_returns_404_for_unknown_case(client: TestClient) -> None:
    response = client.post(
        "/api/cases/unknown@c.us/override",
        json={"action": "agree", "receptionist_id": "sana"},
    )
    assert response.status_code == 404


@patch("app.services.pipeline.whatsapp.send_text", return_value=True)
@patch("app.agent.nodes.classify_message_with_gemini")
def test_override_upgrade_logs_audit_and_resumes(
    mock_classify,
    mock_send,
    client_with_db,
    db_session: Session,
) -> None:
    import asyncio

    asyncio.run(memory.clear_all())
    mock_classify.return_value = TriageResult(
        priority="P3",
        confidence=0.55,
        reasoning="Ambiguous.",
    )
    chat = "79008887766@c.us"
    client_with_db.post(
        "/api/chat/message",
        json={"phone": chat, "body": "pain maybe serious"},
    )

    state = asyncio.run(memory.load(chat))
    assert state.get("awaiting_human_review") is True

    response = client_with_db.post(
        f"/api/cases/{chat}/override",
        json={"action": "upgrade", "receptionist_id": "sana"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "resumed"
    assert body["original_priority"] == "P3"
    assert body["priority"] == "P2"

    row = db_session.scalar(select(Override).where(Override.patient_phone == chat))
    assert row is not None
    assert row.action == "upgrade"
    assert row.receptionist_id == "sana"

    after = asyncio.run(memory.load(chat))
    assert after.get("awaiting_human_review") is False
    assert mock_send.call_count >= 2
