"""LangGraph node functions for intake triage."""

from __future__ import annotations

import logging

from app.agent.specialists import get_profile
from app.agent.specialists.router import pick_specialist
from app.agent.state import (
    P1_KEYWORDS,
    TriageState,
    latest_message,
    missing_slots,
)
from app.agent.triage import classify_message_with_gemini
from app.services import slack

logger = logging.getLogger(__name__)

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
    profile = get_profile(state.get("routed_to"))
    question = profile.slot_questions.get(
        slot_name,
        f"Please share your {slot_name}.",
    )
    return {
        "clarification_rounds": rounds + 1,
        "pending_slot": slot_name,
        "reply": question,
    }


def route_node(state: TriageState) -> dict:
    """Pick specialist before slot-filling; idempotent if already routed."""
    if state.get("routed_to"):
        return {}
    return {"routed_to": pick_specialist(state)}


def notify_human_node(state: TriageState) -> dict:
    """Alert staff via Slack webhook (P1 / P2 / escalated)."""
    phone = state.get("patient_phone", "unknown")
    priority = state.get("priority", "?")
    routed = state.get("routed_to")
    preview = latest_message(state)
    escalated = bool(state.get("escalated"))

    sent = slack.send_triage_alert(
        patient_phone=phone,
        priority=priority,
        routed_to=routed,
        reasoning=state.get("reasoning") or "",
        message_preview=preview,
        escalated=escalated,
    )
    if not sent:
        logger.warning(
            "TRIAGE_ALERT phone=%s priority=%s routed_to=%s escalated=%s",
            phone,
            priority,
            routed or "n/a",
            escalated,
        )
    return {"slack_notified": sent}


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
