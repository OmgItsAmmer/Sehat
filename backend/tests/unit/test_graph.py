"""Phase 4 unit tests: LangGraph triage graph (classify mocked — no live Gemini)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from app.agent.graph import graph
from app.agent.triage import TriageResult

pytestmark = pytest.mark.unit


def _invoke_chest_pain() -> dict:
    return graph.invoke(
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


@patch("app.agent.nodes.slack.send_triage_alert", return_value=True)
def test_p1_keyword_override_end_to_end(_mock_slack) -> None:
    """P1 keywords bypass Gemini and traverse emergency → notify → confirm."""
    with patch("app.agent.nodes.classify_message_with_gemini") as mock_gemini:
        result = _invoke_chest_pain()

    mock_gemini.assert_not_called()
    assert result["priority"] == "P1"
    assert result["escalated"] is True
    assert result["slack_notified"] is True
    assert "1122" in result["reply"]


@patch("app.agent.nodes.classify_message_with_gemini")
def test_oos_path_skips_gemini_slots(mock_classify) -> None:
    mock_classify.return_value = TriageResult(
        priority="OOS",
        confidence=0.95,
        reasoning="Billing question.",
    )
    result = graph.invoke(
        {
            "messages": ["fee kitni hai consultation ki"],
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
    assert "City Medical Center" in result["reply"]
    assert result.get("slack_notified") is not True


@patch("app.agent.nodes.classify_message_with_gemini")
def test_p3_with_slots_routes_to_general(mock_classify) -> None:
    mock_classify.return_value = TriageResult(
        priority="P3",
        confidence=0.88,
        reasoning="Routine back pain appointment.",
    )
    result = graph.invoke(
        {
            "messages": ["appointment chahiye back pain ke liye"],
            "patient_phone": "+923001234567",
            "confidence": 0.0,
            "clarification_rounds": 0,
            "slots": {
                "chief_complaint": "back pain",
                "symptom_duration": "1 week",
                "preferred_day": "Wednesday",
            },
            "slots_complete": False,
            "escalated": False,
            "reply": "",
        }
    )

    assert result["priority"] == "P3"
    assert result["routed_to"] == "general"
    assert result["slots_complete"] is True
    assert result["reply"]


@patch("app.agent.nodes.classify_message_with_gemini")
def test_p3_missing_slots_pauses_with_question(mock_classify) -> None:
    mock_classify.return_value = TriageResult(
        priority="P3",
        confidence=0.88,
        reasoning="Routine appointment.",
    )
    result = graph.invoke(
        {
            "messages": ["appointment chahiye"],
            "patient_phone": "+923001234567",
            "confidence": 0.0,
            "clarification_rounds": 0,
            "slots": {},
            "slots_complete": False,
            "escalated": False,
            "reply": "",
        }
    )

    assert result["priority"] == "P3"
    assert result["slots_complete"] is False
    assert result["reply"]
    assert result.get("pending_slot") == "chief_complaint"
    assert result.get("routed_to") == "general"
