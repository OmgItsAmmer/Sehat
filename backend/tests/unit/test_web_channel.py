"""Web chat channel — separate storage and API from WhatsApp."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from app.agent.triage import TriageResult
from app.services import memory, pipeline, web_memory
from fastapi.testclient import TestClient

pytestmark = pytest.mark.unit


@patch("app.services.pipeline.whatsapp.send_text", return_value=True)
@patch("app.agent.nodes.classify_message_with_openai")
@pytest.mark.asyncio
async def test_web_inbound_never_calls_whatsapp(mock_classify, mock_send) -> None:
    mock_classify.return_value = TriageResult(
        priority="P3",
        confidence=0.9,
        reasoning="Routine.",
    )
    session_id = "ws_aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

    result = await pipeline.process_web_inbound(session_id=session_id, body="headache")

    assert result["priority"] == "P3"
    mock_send.assert_not_called()

    stored = await web_memory.load(session_id)
    assert stored.get("messages") == ["headache"]
    whatsapp_state = await memory.load(session_id)
    assert not whatsapp_state.get("messages")


def test_web_chat_api_roundtrip(client: TestClient) -> None:
    import asyncio

    asyncio.run(web_memory.clear_all())
    session_id = "ws_1a908ae3-1b34-5678-90ab-cdef12345678"

    empty = client.get(f"/api/web-chat/sessions/{session_id}")
    assert empty.status_code == 200
    assert empty.json()["message_count"] == 0

    with patch("app.agent.nodes.classify_message_with_openai") as mock_classify:
        mock_classify.return_value = TriageResult(
            priority="P2",
            confidence=0.85,
            reasoning="Urgent symptoms.",
        )
        with patch("app.services.pipeline.whatsapp.send_text", return_value=True) as mock_send:
            posted = client.post(
                "/api/web-chat/message",
                json={"session_id": session_id, "body": "high fever"},
            )

    assert posted.status_code == 200
    body = posted.json()
    assert body["session_id"] == session_id
    assert body["channel"] == "web"
    assert body["priority"] == "P2"
    mock_send.assert_not_called()

    hydrated = client.get(f"/api/web-chat/sessions/{session_id}")
    assert hydrated.status_code == 200
    assert hydrated.json()["message_count"] == 1


def test_legacy_chat_message_route_removed(client: TestClient) -> None:
    response = client.post(
        "/api/chat/message",
        json={"phone": "ws_removed@c.us", "body": "hi"},
    )
    assert response.status_code == 404
