"""Phase 8 unit tests: specialist routing and slot schemas."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from app.agent.graph import graph
from app.agent.specialists import get_profile
from app.agent.specialists.router import pick_specialist
from app.agent.triage import TriageResult

pytestmark = pytest.mark.unit


def test_pick_specialist_cardiology_keywords() -> None:
    state = {
        "messages": ["appointment for chest pain follow up"],
        "priority": "P3",
    }
    assert pick_specialist(state) == "cardiology"


def test_pick_specialist_pediatrics_keywords() -> None:
    state = {
        "messages": ["bachay ko tez bukhaar hai"],
        "priority": "P2",
    }
    assert pick_specialist(state) == "pediatrics"


def test_pick_specialist_general_default() -> None:
    state = {
        "messages": ["appointment chahiye back pain ke liye"],
        "priority": "P3",
    }
    assert pick_specialist(state) == "general"


def test_cardiology_profile_slots() -> None:
    profile = get_profile("cardiology")
    assert "pain_radiation" in profile.required_slots
    assert "pain_radiation" in profile.slot_questions


@patch("app.agent.nodes.classify_message_with_openai")
def test_p2_pediatrics_first_slot_question(mock_classify) -> None:
    mock_classify.return_value = TriageResult(
        priority="P2",
        confidence=0.9,
        reasoning="Child with fever.",
    )
    result = graph.invoke(
        {
            "messages": ["bachay ko 3 din se tez bukhaar hai"],
            "patient_phone": "+923001234567",
            "confidence": 0.0,
            "clarification_rounds": 0,
            "slots": {},
            "slots_complete": False,
            "escalated": False,
            "reply": "",
        }
    )

    assert result["routed_to"] == "pediatrics"
    assert result.get("pending_slot") == "child_age"
    assert "old" in result["reply"].lower()


@patch("app.agent.nodes.classify_message_with_openai")
def test_p3_cardiology_routine_chest_keywords(mock_classify) -> None:
    mock_classify.return_value = TriageResult(
        priority="P3",
        confidence=0.85,
        reasoning="Non-emergency cardiac follow-up.",
    )
    result = graph.invoke(
        {
            "messages": ["dil ki dawa ke baad seene mein halka dard"],
            "patient_phone": "+923001234567",
            "confidence": 0.0,
            "clarification_rounds": 0,
            "slots": {},
            "slots_complete": False,
            "escalated": False,
            "reply": "",
        }
    )

    assert result["routed_to"] == "cardiology"
    assert result.get("pending_slot") == "pain_location"
