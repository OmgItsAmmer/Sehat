"""LangGraph node functions for intake triage."""

from __future__ import annotations

import logging

from app.agent.composer import compose_reply
from app.agent.specialists import get_profile
from app.agent.specialists.router import pick_specialist
from app.agent.state import (
    P1_KEYWORDS,
    TriageState,
    latest_message,
    missing_slots,
)
from app.agent.triage import classify_message_with_openai
from app.services import slack

logger = logging.getLogger(__name__)

MAX_CLARIFICATION_ROUNDS = 10


def _matches_p1_keywords(text: str) -> bool:
    lowered = text.lower()
    return any(kw in lowered for kw in P1_KEYWORDS)


def _is_pure_greeting(text: str) -> bool:
    t = text.strip().lower().rstrip("!?.")
    if not t:
        return False
    greetings = (
        "hello",
        "hi",
        "hey",
        "salam",
        "aoa",
        "assalam o alaikum",
        "assalamu alaikum",
        "asalam o alaikum",
        "assalamualaikum",
    )
    return t in greetings or t.startswith("assalam") or t.startswith("salam")


def _intake_already_logged(state: TriageState) -> bool:
    return bool(state.get("slots_complete") and (state.get("slots") or {}))


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def classify_node(state: TriageState) -> dict:
    """Run OpenAI triage on the latest patient message."""
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

    if _is_pure_greeting(message):
        return {
            "priority": "P3",
            "confidence": 0.95,
            "reasoning": "Pure greeting — invite health concern.",
        }

    if _intake_already_logged(state):
        return {}

    result = classify_message_with_openai(message)
    updates: dict = {
        "priority": result.priority,
        "confidence": result.confidence,
        "reasoning": result.reasoning,
    }
    if result.confidence < 0.75 and result.priority not in ("P1", "OOS"):
        updates["escalated"] = True
    return updates


# ---------------------------------------------------------------------------
# Exit / terminal intent nodes  (set reply_intent, NOT reply)
# ---------------------------------------------------------------------------


def emergency_exit_node(state: TriageState) -> dict:
    """P1 fast path — skip slot-filling, advise emergency services."""
    return {
        "escalated": True,
        "slots_complete": True,
        "reply_intent": (
            "EMERGENCY: tell the patient this sounds urgent. "
            "Ask them to call 1122 or go to the nearest emergency room immediately. "
            "Reassure them that a clinic staff member has been alerted."
        ),
    }


def oos_exit_node(state: TriageState) -> dict:
    """Out-of-scope redirect — no slot-filling."""
    return {
        "slots_complete": True,
        "reply_intent": (
            "OOS: the patient asked about something outside the bot's scope "
            "(billing, visa letters, lab printouts, pharmacy stock, or unrelated topics). "
            "Warmly tell them those are handled at the City Medical Center reception. "
            "Then ask if they have any health concern you can help with today. "
            "End with: Type *reset* to start a fresh conversation anytime."
        ),
    }


def slot_check_node(state: TriageState) -> dict:
    """Mark whether all required intake slots are filled."""
    # Forced completion (max clarification rounds) — do not re-open slot gathering.
    if state.get("slots_complete") and state.get("escalated"):
        return {}
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
            "reply_intent": (
                "ESCALATE: the bot still needs a few intake details but the patient "
                "hasn't provided them. Politely say a receptionist will follow up shortly."
            ),
        }

    slot_name = missing[0]
    profile = get_profile(state.get("routed_to"))
    raw_question = profile.slot_questions.get(
        slot_name,
        f"Please share your {slot_name}.",
    )
    return {
        "clarification_rounds": rounds + 1,
        "pending_slot": slot_name,
        "reply_intent": (
            f"SLOT_QUESTION: ask the patient for their {slot_name}. "
            f"Suggested phrasing: {raw_question}"
        ),
    }


def route_node(state: TriageState) -> dict:
    """Pick specialist before slot-filling; idempotent if already routed."""
    if state.get("routed_to"):
        return {}
    return {"routed_to": pick_specialist(state)}


def notify_human_node(state: TriageState) -> dict:
    """Alert staff via Slack webhook (P1 / P2 / escalated)."""
    phone = state.get("patient_phone", "unknown")
    priority = state.get("priority") or "?"
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


def await_human_review_node(state: TriageState) -> dict:
    """Pause for receptionist override when classification confidence is low."""
    return {
        "awaiting_human_review": True,
        "escalated": True,
        "reply_intent": (
            "HOLD: the bot is not confident about the classification. "
            "Reassure the patient that their message was received and a receptionist "
            "is reviewing their case and will confirm next steps shortly."
        ),
    }


def confirm_user_node(state: TriageState) -> dict:
    """Set reply_intent for the happy-path confirmation (P2/P3 fully slotted)."""
    prior = (state.get("reply_intent") or "").strip()
    if prior.startswith(("EMERGENCY", "OOS", "ESCALATE", "HOLD")):
        return {}
    if prior.startswith(("CONFIRMED", "ADDENDUM")):
        return {}

    priority = state.get("priority")
    routed = state.get("routed_to") or "our clinic"
    if state.get("intake_confirmed") and priority in ("P2", "P3"):
        return {
            "reply_intent": (
                "ADDENDUM: intake is already complete (symptom, duration, preferred day in FILLED_SLOTS). "
                "Acknowledge the patient's latest message (e.g. preferred day or time). "
                "Say reception will confirm the appointment. "
                "Do NOT ask for more intake fields. Do NOT mention billing or admin desk."
            ),
        }
    if priority in ("P2", "P3"):
        return {
            "intake_confirmed": True,
            "reply_intent": (
                f"CONFIRMED: the patient's case has been logged as {priority} priority "
                f"and routed to {routed}. "
                "Warmly confirm receipt and say they will hear back shortly "
                "to confirm the appointment. "
                "Do NOT ask for appointment time or any extra intake fields."
            ),
        }
    return {
        "reply_intent": (
            "RECEIVED: the patient's message has been recorded. "
            "Acknowledge warmly and say the team will be in touch."
        ),
    }


# ---------------------------------------------------------------------------
# Natural reply composer — always the last node before END
# ---------------------------------------------------------------------------


def compose_reply_node(state: TriageState) -> dict:
    """
    Convert reply_intent → natural patient-facing reply via LLM.

    This is the only node that writes the `reply` field.  Every other node
    writes `reply_intent` (a structured instruction for this node).
    Passes only the LAST patient message + filled slots to prevent hallucination.
    """
    intent = (state.get("reply_intent") or "").strip()
    if not intent:
        return {}

    last_message = latest_message(state)
    filled_slots = dict(state.get("slots") or {})

    # CLI visibility: log current triage state so devs can track LLM progress
    priority = state.get("priority") or "?"
    routed = state.get("routed_to") or "unrouted"
    logger.info(
        "STATE | phone=%-15s priority=%-3s routed=%-12s slots=%s",
        state.get("patient_phone", "?"),
        priority,
        routed,
        filled_slots or "(empty)",
    )
    if filled_slots:
        for slot_key, slot_val in filled_slots.items():
            logger.info("  SLOT filled  %-20s = %r", slot_key, slot_val)

    natural = compose_reply(
        last_message=last_message,
        intent=intent,
        filled_slots=filled_slots,
    )
    return {"reply": natural, "reply_intent": ""}
