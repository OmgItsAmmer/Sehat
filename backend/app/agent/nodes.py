"""LangGraph node functions for intake triage."""

from __future__ import annotations

import logging

from app.agent.state import (
    P1_KEYWORDS,
    TriageState,
    latest_message,
    missing_slots,
)
from app.agent.triage import classify_message_with_gemini

logger = logging.getLogger(__name__)

# One question per missing slot (Phase 4 — specialists replace prompts in Phase 8).
SLOT_QUESTIONS: dict[str, str] = {
    "chief_complaint": "What is the main problem or symptom we should know about?",
    "symptom_duration": "How long have you had this (hours, days, or weeks)?",
    "preferred_day": "Which day works best for an appointment (e.g. Monday, Wednesday)?",
}

MAX_CLARIFICATION_ROUNDS = 2


def _matches_p1_keywords(text: str) -> bool:
    lowered = text.lower()
    return any(kw in lowered for kw in P1_KEYWORDS)


def classify_node(state: TriageState) -> dict:
    """Run Gemini triage on the latest patient message."""
    message = latest_message(state)
    if not message:
        return {
            "priority": "OOS",
            "confidence": 0.0,
            "reasoning": "No message to classify.",
        }

    if _matches_p1_keywords(message):
        return {
            "priority": "P1",
            "confidence": 1.0,
            "reasoning": "P1 keyword override (hardcoded safety list).",
        }

    result = classify_message_with_gemini(message)
    updates: dict = {
        "priority": result.priority,
        "confidence": result.confidence,
        "reasoning": result.reasoning,
    }
    if result.confidence < 0.75 and result.priority not in ("P1", "OOS"):
        updates["escalated"] = True
    return updates


def emergency_exit_node(state: TriageState) -> dict:
    """P1 fast path — skip slot-filling, advise emergency services."""
    return {
        "escalated": True,
        "slots_complete": True,
        "reply": (
            "This sounds urgent. Please call 1122 or go to the nearest emergency room now. "
            "A clinic staff member has been alerted."
        ),
    }


def oos_exit_node(state: TriageState) -> dict:
    """Out-of-scope redirect — no slot-filling."""
    return {
        "slots_complete": True,
        "reply": (
            "For billing, visa medical certificates, lab results, and pharmacy questions, "
            "please contact City Medical Center directly. "
            "I can help with appointment triage and symptoms only."
        ),
    }


def slot_check_node(state: TriageState) -> dict:
    """Mark whether all required intake slots are filled."""
    missing = missing_slots(state)
    return {"slots_complete": len(missing) == 0}


def gather_slots_node(state: TriageState) -> dict:
    """Ask for the next missing slot (one question per graph pass)."""
    missing = missing_slots(state)
    rounds = state.get("clarification_rounds") or 0

    if not missing:
        return {"slots_complete": True}

    if rounds >= MAX_CLARIFICATION_ROUNDS:
        return {
            "escalated": True,
            "slots_complete": True,
            "reply": (
                "I still need a few details. A receptionist will follow up with you shortly."
            ),
        }

    slot_name = missing[0]
    question = SLOT_QUESTIONS.get(slot_name, f"Please share your {slot_name}.")
    return {
        "clarification_rounds": rounds + 1,
        "reply": question,
    }


def route_node(state: TriageState) -> dict:
    """Assign department from priority + message keywords (specialists in Phase 8)."""
    text = " ".join(state.get("messages") or []).lower()
    priority = state.get("priority")

    if priority == "P1" or any(k in text for k in ("seene", "chest", "dil", "heart")):
        department = "cardiology"
    elif any(k in text for k in ("bach", "bachay", "child", "infant", "baby")):
        department = "pediatrics"
    else:
        department = "general"

    return {"routed_to": department}


def notify_human_node(state: TriageState) -> dict:
    """Alert staff (Slack in Phase 5; log-only stub here)."""
    phone = state.get("patient_phone", "unknown")
    priority = state.get("priority", "?")
    routed = state.get("routed_to") or "n/a"
    logger.warning(
        "TRIAGE_ALERT phone=%s priority=%s routed_to=%s escalated=%s",
        phone,
        priority,
        routed,
        state.get("escalated", False),
    )
    return {"slack_notified": True}


def confirm_user_node(state: TriageState) -> dict:
    """Final patient-facing reply when a node has not already set one."""
    if state.get("reply"):
        return {}

    priority = state.get("priority")
    routed = state.get("routed_to") or "our clinic"
    if priority in ("P2", "P3"):
        return {
            "reply": (
                f"Thank you. Your case is logged as {priority} and routed to {routed}. "
                "We will confirm your appointment shortly."
            ),
        }
    return {"reply": "Thank you. We have recorded your message."}
