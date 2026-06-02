"""Shared triage state schema for the LangGraph intake graph."""

from __future__ import annotations

import operator
from typing import Annotated

from typing_extensions import TypedDict

# Fields the graph reads/writes across nodes (Phase 4+).
REQUIRED_SLOTS: tuple[str, ...] = (
    "chief_complaint",
    "symptom_duration",
    "preferred_day",
)

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
    reply: str


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
        "reply": "",
    }


def latest_message(state: TriageState) -> str:
    msgs = state.get("messages") or []
    if not msgs:
        return ""
    return msgs[-1]


def missing_slots(state: TriageState) -> list[str]:
    filled = state.get("slots") or {}
    return [name for name in REQUIRED_SLOTS if not filled.get(name)]
