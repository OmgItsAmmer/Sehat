"""Phase 4 unit tests: LangGraph triage graph (classify mocked — no live OpenAI)."""

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
    """P1 keywords bypass LLM and traverse emergency → notify → confirm."""
    with patch("app.agent.nodes.classify_message_with_openai") as mock_gemini:
        result = _invoke_chest_pain()

    mock_gemini.assert_not_called()
    assert result["priority"] == "P1"
    assert result["escalated"] is True
    assert result["slack_notified"] is True
    assert "1122" in result["reply"]


@patch("app.agent.nodes.classify_message_with_openai")
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
    assert "Dr Muhid Clinics" in result["reply"]
    assert result.get("slack_notified") is not True


@patch("app.agent.nodes.classify_message_with_openai")
def test_faq_skips_slot_gathering_with_clinic_context(mock_classify) -> None:
    mock_classify.return_value = TriageResult(
        priority="P3",
        confidence=0.95,
        reasoning="Clinic timings query.",
    )
    result = graph.invoke(
        {
            "messages": ["what are the clinic timings?"],
            "patient_phone": "+923001234567",
            "confidence": 0.0,
            "clarification_rounds": 0,
            "slots": {},
            "slots_complete": False,
            "escalated": False,
            "reply": "",
            "clinic_context": "CLINIC_KNOWLEDGE:\nThe clinic is open from 9am to 11pm daily.",
        }
    )

    assert result["priority"] == "P3"
    assert result["slots_complete"] is True
    assert result["reply"].startswith("INFO_DESK:")


@patch("app.agent.nodes.classify_message_with_openai")
def test_appointment_lookup_asks_for_phone_and_then_results(mock_classify) -> None:
    # 1. First turn: user asks "what is my queue number?" without phone
    mock_classify.return_value = TriageResult(
        priority="P3",
        confidence=0.95,
        reasoning="Inquiry about appointment queue.",
    )
    result1 = graph.invoke(
        {
            "messages": ["what is my queue number?"],
            "patient_phone": "+923001234567",
            "confidence": 0.0,
            "clarification_rounds": 0,
            "slots": {},
            "slots_complete": False,
            "escalated": False,
            "reply": "",
            "clinic_context": "APPOINTMENT_LOOKUP: Please ask the patient to share the mobile number they used when booking, or their guest code, so we can look up their appointment.",
        }
    )

    assert result1["priority"] == "P3"
    assert result1["slots_complete"] is True
    assert "INFO_DESK: ask the patient to share the mobile number" in result1["reply"]

    # 2. Second turn: user replies with phone number
    result2 = graph.invoke(
        {
            "messages": ["what is my queue number?", "03001234567"],
            "patient_phone": "+923001234567",
            "confidence": 0.95,
            "clarification_rounds": 0,
            "slots": {},
            "slots_complete": True,
            "escalated": False,
            "reply": "",
            "clinic_context": "APPOINTMENT_LOOKUP: Dr Saeed Sarwar on 2026-06-05 at 09:15. (contact: 03001234567)",
        }
    )

    assert result2["slots_complete"] is True
    assert "INFO_DESK: report the appointment status/timings" in result2["reply"]


@patch("app.agent.nodes.classify_message_with_openai")
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
                "contact_phone": "03001234567",
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
    assert result.get("appointment_offered") is True
    assert result.get("awaiting_appointment_consent") is True
    assert result["reply"]


@patch("app.agent.nodes.classify_message_with_openai")
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


@patch("app.agent.nodes.compose_reply", return_value="receptionist will follow up shortly")
@patch("app.agent.nodes.slack.send_triage_alert", return_value=True)
def test_max_clarification_rounds_does_not_recursion_loop(_mock_slack, _mock_compose) -> None:
    """Forced slot completion must not bounce gather_slots ↔ slot_check forever."""
    result = graph.invoke(
        {
            "messages": ["appointment chahiye"],
            "patient_phone": "+923001234567",
            "priority": "P3",
            "confidence": 0.88,
            "clarification_rounds": 10,
            "slots": {},
            "slots_complete": False,
            "routed_to": "general",
            "escalated": False,
            "reply": "",
        }
    )

    assert result["escalated"] is True
    assert result["slots_complete"] is True
    assert result["reply"]


@patch("app.agent.nodes.classify_message_with_openai")
def test_low_confidence_routes_to_human_review(mock_classify) -> None:
    mock_classify.return_value = TriageResult(
        priority="P3",
        confidence=0.6,
        reasoning="Uncertain.",
    )
    result = graph.invoke(
        {
            "messages": ["not sure if urgent back pain"],
            "patient_phone": "+923001234567",
            "confidence": 0.0,
            "clarification_rounds": 0,
            "slots": {},
            "slots_complete": False,
            "escalated": False,
            "reply": "",
        }
    )

    assert result["awaiting_human_review"] is True
    assert result.get("pending_slot") is None


@patch("app.agent.nodes.compose_reply", return_value="Appointment 9:15 par Dr Saeed ke paas.")
@patch("app.agent.nodes.book_next_slot")
@patch("app.database.session.db_is_available", return_value=True)
@patch("app.database.session.get_sessionmaker")
def test_book_appointment_after_consent(
    mock_get_sm,
    _mock_db_ok,
    mock_book,
    _mock_compose,
) -> None:
    from unittest.mock import MagicMock

    mock_book.return_value = {
        "appointment_date": "2026-06-05",
        "appointment_time": "09:15",
        "doctor_label": "Dr Saeed Sarwar (General)",
        "patient_type": "general medicine",
        "contact_phone": "03001234567",
        "guest_code": "",
        "slot_index": "1",
    }
    ctx = MagicMock()
    ctx.__enter__.return_value = MagicMock()
    ctx.__exit__.return_value = None
    mock_get_sm.return_value = MagicMock(return_value=ctx)

    result = graph.invoke(
        {
            "messages": ["haan book kar dein"],
            "patient_phone": "+923001234567",
            "priority": "P3",
            "confidence": 0.9,
            "slots": {
                "chief_complaint": "back pain",
                "symptom_duration": "1 week",
                "contact_phone": "03001234567",
                "preferred_day": "Thursday",
            },
            "slots_complete": True,
            "routed_to": "general",
            "appointment_offered": True,
            "appointment_consent": True,
            "escalated": False,
            "reply": "",
        }
    )

    assert result["appointment_booked"] is True
    assert result["slots"]["appointment_time"] == "09:15"
    mock_book.assert_called_once()


@patch("app.agent.nodes.compose_reply", return_value="Appointment confirmed.")
@patch("app.agent.nodes.book_next_slot")
@patch("app.database.session.db_is_available", return_value=True)
@patch("app.database.session.get_sessionmaker")
@patch("app.agent.nodes.classify_message_with_openai")
@patch("app.agent.nodes.slack.send_triage_alert", return_value=True)
def test_book_appointment_triggers_classification_and_slack(
    mock_slack,
    mock_classify,
    mock_get_sm,
    _mock_db_ok,
    mock_book,
    _mock_compose,
) -> None:
    from unittest.mock import MagicMock
    mock_book.return_value = {
        "appointment_date": "2026-06-05",
        "appointment_time": "09:15",
        "doctor_label": "Dr Saeed Sarwar (General)",
        "patient_type": "general medicine",
        "contact_phone": "03001234567",
        "guest_code": "",
        "slot_index": "1",
    }
    ctx = MagicMock()
    ctx.__enter__.return_value = MagicMock()
    ctx.__exit__.return_value = None
    mock_get_sm.return_value = MagicMock(return_value=ctx)

    mock_classify.return_value = TriageResult(
        priority="P2",
        confidence=0.9,
        reasoning="Patient booked after describing chronic back pain.",
    )

    result = graph.invoke(
        {
            "messages": [
                "appointment chahiye",
                "chronic back pain for 2 weeks",
                "haan book kar dein",
            ],
            "patient_phone": "+923001234567",
            "priority": "P3",
            "confidence": 0.8,
            "slots": {
                "chief_complaint": "back pain",
                "symptom_duration": "2 weeks",
                "contact_phone": "03001234567",
                "preferred_day": "Thursday",
            },
            "slots_complete": True,
            "routed_to": "general",
            "appointment_offered": True,
            "appointment_consent": True,
            "escalated": False,
            "reply": "",
        }
    )

    assert result["appointment_booked"] is True
    assert result["intake_finalized"] is True
    assert result["priority"] == "P2"
    assert result["confidence"] == 0.9
    assert result["reasoning"] == "Patient booked after describing chronic back pain."
    assert result["slack_notified"] is True

    # Assert classification was called with ALL chats joined by newline
    mock_classify.assert_called_once_with(
        "appointment chahiye\nchronic back pain for 2 weeks\nhaan book kar dein"
    )
    mock_slack.assert_called_once()
