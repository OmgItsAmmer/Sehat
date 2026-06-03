"""Phase 8 — specialist routing and slot schemas."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from app.agent.graph import graph
from app.agent.specialists import get_profile
from app.agent.specialists.router import pick_specialist
from app.agent.triage import TriageResult

pytestmark = [pytest.mark.unit, pytest.mark.phase8]


def test_router_picks_cardiology_for_chest_keywords() -> None:
    state = {"messages": ["appointment for chest pain follow up"], "priority": "P3"}
    assert pick_specialist(state) == "cardiology"


def test_router_picks_pediatrics_for_child_keywords() -> None:
    state = {"messages": ["bachay ko tez bukhaar hai"], "priority": "P2"}
    assert pick_specialist(state) == "pediatrics"


def test_cardiology_required_slots_differ_from_general() -> None:
    cardio = get_profile("cardiology")
    general = get_profile("general")
    assert "pain_radiation" in cardio.required_slots
    assert "pain_radiation" not in general.required_slots


@patch("app.agent.nodes.classify_message_with_openai")
def test_pediatrics_first_pending_slot(mock_classify) -> None:
    mock_classify.return_value = TriageResult(
        priority="P2", confidence=0.9, reasoning="Child fever."
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
