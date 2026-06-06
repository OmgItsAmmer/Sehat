"""Phase 4 — LangGraph triage graph runs end to end."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from app.agent.graph import graph, invoke_graph
from app.agent.state import fresh_state
from app.agent.triage import TriageResult

pytestmark = [pytest.mark.unit, pytest.mark.phase4]


def test_fresh_state_has_required_fields() -> None:
    state = fresh_state("+923001234567")
    assert state["messages"] == []
    assert state["priority"] is None
    assert state["slots_complete"] is False


@patch("app.agent.nodes.slack.send_triage_alert", return_value=True)
def test_p1_keyword_traverses_emergency_path(_mock_slack) -> None:
    with patch("app.agent.nodes.classify_message_with_openai") as mock_gemini:
        result = invoke_graph(
            {
                "messages": ["seene mein dard"],
                "patient_phone": "+923001234567",
                "priority": None,
                "confidence": 0.0,
                "clarification_rounds": 0,
                "slots": {},
                "slots_complete": False,
                "routed_to": None,
                "escalated": False,
                "slack_notified": False,
                "reply": "",
            }
        )

    mock_gemini.assert_not_called()
    assert result["priority"] == "P1"
    assert result["escalated"] is True
    assert "1122" in result["reply"]


@patch("app.agent.nodes.classify_message_with_openai")
def test_oos_exits_without_slot_filling(mock_classify) -> None:
    mock_classify.return_value = TriageResult(
        priority="OOS",
        confidence=0.95,
        reasoning="Fee question.",
    )
    result = graph.invoke(
        {
            "messages": ["fee kitni hai"],
            "patient_phone": "+923001234567",
            "confidence": 0.0,
            "clarification_rounds": 0,
            "slots": {},
            "slots_complete": False,
            "escalated": False,
            "reply": "",
        }
    )

    assert result["priority"] == "OOS"
    assert result["slots_complete"] is True
    assert "Dr Muhid Clinics" in result["reply"]
