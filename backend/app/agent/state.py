"""Shared triage state schema for the LangGraph intake graph."""

from __future__ import annotations

import operator
from typing import Annotated, Any, cast

from typing_extensions import TypedDict

# Hard override — LLM output ignored when matched (see README triage logic).
P1_KEYWORDS: tuple[str, ...] = (
    "seene mein dard",
    "chest pain",
    "saans nahi",
    "nahi saans",
    "unconscious",
    "behosh",
    "seizure",
    "convulsion",
    "heavy bleeding",
    "khoon bah",
)


class TriageState(TypedDict, total=False):
    """LangGraph state for one patient intake thread."""

    messages: Annotated[list[str], operator.add]
    patient_phone: str
    priority: str | None
    confidence: float
    reasoning: str
    clarification_rounds: int
    slots: dict[str, str]
    slots_complete: bool
    routed_to: str | None
    escalated: bool
    slack_notified: bool
    pending_slot: str | None
    # reply_intent: structured clinical instruction for compose_reply_node
    # reply: the final natural-language message sent to the patient
    reply_intent: str
    reply: str
    awaiting_human_review: bool
    human_review_resolved: bool
    intake_confirmed: bool
    last_activity_at: str | None
    clinic_context: str
    awaiting_appointment_consent: bool
    appointment_consent: bool | None
    appointment_offered: bool
    appointment_booked: bool
    guest_code: str | None
    intake_finalized: bool


def fresh_state(patient_phone: str) -> TriageState:
    """Blank state for a new conversation (used by Redis memory in Phase 6)."""
    return {
        "messages": [],
        "patient_phone": patient_phone,
        "priority": None,
        "confidence": 0.0,
        "reasoning": "",
        "clarification_rounds": 0,
        "slots": {},
        "slots_complete": False,
        "routed_to": None,
        "escalated": False,
        "slack_notified": False,
        "pending_slot": None,
        "reply_intent": "",
        "reply": "",
        "awaiting_human_review": False,
        "human_review_resolved": False,
        "intake_confirmed": False,
        "clinic_context": "",
        "awaiting_appointment_consent": False,
        "appointment_consent": None,
        "appointment_offered": False,
        "appointment_booked": False,
        "guest_code": None,
        "intake_finalized": False,
    }


def merge_state(state: TriageState, patch: dict[str, Any]) -> TriageState:
    """Merge partial updates (Redis JSON, slot answers) into triage state."""
    return cast(TriageState, {**state, **patch})


def latest_message(state: TriageState) -> str:
    msgs = state.get("messages") or []
    if not msgs:
        return ""
    return msgs[-1]


def missing_slots(state: TriageState) -> list[str]:
    from app.agent.specialists import get_profile

    profile = get_profile(state.get("routed_to"))
    filled = state.get("slots") or {}
    return [name for name in profile.required_slots if not filled.get(name)]
