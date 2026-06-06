"""Intake pipeline — shared triage graph; WhatsApp and web chat use separate session stores."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.agent.graph import invoke_graph
from app.agent.state import TriageState, fresh_state, latest_message, merge_state
from app.channels import WEB, WHATSAPP
from app.services import memory, web_memory, whatsapp
from app.services.clinic_info import build_clinic_context
from app.services.persist import (
    persist_incoming_message,
    persist_intake_state,
    persist_outbound_message,
)
from app.services.scheduling import parse_appointment_consent

logger = logging.getLogger(__name__)

OverrideAction = Literal["agree", "upgrade", "downgrade"]
Channel = Literal["whatsapp", "web"]

_UPGRADE: dict[str, str] = {"OOS": "P3", "P3": "P2", "P2": "P1", "P1": "P1"}
_DOWNGRADE: dict[str, str] = {"P1": "P2", "P2": "P3", "P3": "OOS", "OOS": "OOS"}

HOLD_REPLY = "Your case is with our reception team. We will message you again shortly."

_RESET_KEYWORDS = {"reset", "restart", "start over", "new chat", "clear"}
_RESET_ACK = (
    "Chat reset kar diya gaya hai. Aaj aapki kya health concern hai?\n"
    "(Session has been reset. How can I help you today?)"
)

LoadFn = Callable[[str], Awaitable[TriageState]]
SaveFn = Callable[[str, TriageState], Awaitable[None]]


def _store_for_channel(channel: Channel) -> tuple[LoadFn, SaveFn]:
    if channel == WEB:
        return web_memory.load, web_memory.save
    return memory.load, memory.save


def apply_intake_addendum(state: TriageState) -> dict[str, Any]:
    """After intake is complete, store optional appointment time/day notes in slots."""
    if state.get("pending_slot") or not state.get("slots_complete"):
        return {}
    text = latest_message(state).strip()
    if not text:
        return {}
    lowered = text.lower()
    if not any(
        token in lowered
        for token in (":", "am", "pm", "baje", "subah", "sham", "raat", "morning", "evening")
    ):
        return {}
    slots = dict(state.get("slots") or {})
    slots["preferred_time"] = text
    return {"slots": slots}


def apply_appointment_consent(state: TriageState) -> dict[str, Any]:
    """Parse yes/no when waiting for appointment booking consent."""
    if not state.get("awaiting_appointment_consent"):
        return {}
    text = latest_message(state).strip()
    if not text:
        return {}
    consent = parse_appointment_consent(text)
    if consent is None:
        return {}
    return {
        "appointment_consent": consent,
        "awaiting_appointment_consent": False,
    }


def apply_pending_slot_answer(state: TriageState) -> dict[str, Any]:
    """When the bot asked a slot question, store the patient's new message in `slots`."""
    pending = state.get("pending_slot")
    if not pending:
        return {}

    msgs = state.get("messages") or []
    if len(msgs) < 2:
        return {}

    text = latest_message(state).strip()
    if not text:
        return {}

    slots = dict(state.get("slots") or {})
    slots[pending] = text
    return {"slots": slots, "pending_slot": None}


def adjust_priority(priority: str | None, action: OverrideAction) -> str | None:
    if action == "agree" or not priority:
        return priority
    if action == "upgrade":
        return _UPGRADE.get(priority, priority)
    return _DOWNGRADE.get(priority, priority)


async def _process_inbound(
    *,
    session_id: str,
    body: str,
    channel: Channel,
    db: Session | None = None,
    raw_payload: dict[str, Any] | None = None,
) -> TriageState:
    """Load session → run graph → save.

    WhatsApp also persists to Postgres and sends Green API replies.
    """
    load, save = _store_for_channel(channel)
    deliver_whatsapp = channel == WHATSAPP
    log_label = "phone" if channel == WHATSAPP else "session"

    if body.strip().lower() in _RESET_KEYWORDS:
        state = fresh_state(session_id)
        await save(session_id, state)
        if db is not None:
            persist_incoming_message(
                db=db, patient_phone=session_id, body=body, raw_payload=raw_payload
            )
            persist_outbound_message(db=db, patient_phone=session_id, body=_RESET_ACK)
            persist_intake_state(db=db, patient_phone=session_id, state=state)
        if deliver_whatsapp:
            whatsapp.send_text(chat_id=session_id, message=_RESET_ACK)
        logger.info("SESSION RESET  channel=%s %s=%s", channel, log_label, session_id)
        return state

    state = await load(session_id)
    messages = list(state.get("messages") or [])
    messages.append(body)
    state["messages"] = messages
    state["patient_phone"] = session_id

    if state.get("awaiting_human_review"):
        state["reply"] = HOLD_REPLY
        await save(session_id, state)
        if db is not None:
            persist_incoming_message(
                db=db,
                patient_phone=session_id,
                body=body,
                raw_payload=raw_payload,
            )
            persist_outbound_message(db=db, patient_phone=session_id, body=HOLD_REPLY)
        if deliver_whatsapp:
            whatsapp.send_text(chat_id=session_id, message=HOLD_REPLY)
        return state

    slot_patch = apply_pending_slot_answer(state)
    if slot_patch:
        state = merge_state(state, slot_patch)
        # Reset gather cap so every patient answer gets a fresh budget.
        state["clarification_rounds"] = 0
    addendum_patch = apply_intake_addendum(state)
    if addendum_patch:
        state = merge_state(state, addendum_patch)
    consent_patch = apply_appointment_consent(state)
    if consent_patch:
        state = merge_state(state, consent_patch)

    skip_clinic_ctx = bool(slot_patch and "contact_phone" in (slot_patch.get("slots") or {}))
    if not skip_clinic_ctx:
        contact = (state.get("slots") or {}).get("contact_phone")
        clinic_ctx = build_clinic_context(
            db=db,
            message=body,
            contact_phone_from_slots=contact,
            session_messages=state.get("messages"),
        )
        if clinic_ctx:
            state["clinic_context"] = clinic_ctx
        else:
            state.pop("clinic_context", None)
    else:
        state.pop("clinic_context", None)

    if slot_patch:
        for k, v in (slot_patch.get("slots") or {}).items():
            logger.info(
                "SLOT ANSWER  channel=%-9s %-15s  %s = %r",
                channel,
                session_id,
                k,
                v,
            )

    result = invoke_graph(state)
    await save(session_id, result)

    if db is not None:
        from app.database.session import rollback_db

        try:
            persist_incoming_message(
                db=db,
                patient_phone=session_id,
                body=body,
                raw_payload=raw_payload,
            )
            persist_intake_state(db=db, patient_phone=session_id, state=result)
            reply = (result.get("reply") or "").strip()
            if reply:
                persist_outbound_message(db=db, patient_phone=session_id, body=reply)
        except Exception:
            rollback_db(db)
            raise

    reply = (result.get("reply") or "").strip()
    if deliver_whatsapp and reply:
        whatsapp.send_text(chat_id=session_id, message=reply)

    return result


async def process_whatsapp_inbound(
    *,
    chat_id: str,
    body: str,
    db: Session | None = None,
    raw_payload: dict[str, Any] | None = None,
) -> TriageState:
    """WhatsApp channel — clinic dashboard cases, Postgres history, Green API outbound."""
    return await _process_inbound(
        session_id=chat_id,
        body=body,
        channel=WHATSAPP,
        db=db,
        raw_payload=raw_payload,
    )


async def process_web_inbound(
    *,
    session_id: str,
    body: str,
    db: Session | None = None,
) -> TriageState:
    """Web chat channel — separate Redis store; persists to Postgres when db is available."""
    return await _process_inbound(
        session_id=session_id,
        body=body,
        channel=WEB,
        db=db,
        raw_payload=None,
    )


# Back-compat for existing tests and imports
async def process_inbound(
    *,
    chat_id: str,
    body: str,
    db: Session | None = None,
    raw_payload: dict[str, Any] | None = None,
) -> TriageState:
    return await process_whatsapp_inbound(
        chat_id=chat_id,
        body=body,
        db=db,
        raw_payload=raw_payload,
    )


async def resume_after_override(
    *,
    chat_id: str,
    action: OverrideAction,
    receptionist_id: str,
    db: Session | None = None,
) -> TriageState:
    """Apply receptionist decision on a WhatsApp case, re-run graph, notify patient via WhatsApp."""
    state = await memory.load(chat_id)
    if not state.get("messages"):
        raise ValueError("No active case for this phone")

    original = state.get("priority")
    corrected = adjust_priority(original, action)

    state["priority"] = corrected
    state["awaiting_human_review"] = False
    state["human_review_resolved"] = True

    if corrected == "P1":
        state["escalated"] = True
        state["slots_complete"] = True
        state.pop("pending_slot", None)
    elif corrected == "OOS":
        state["slots_complete"] = True
        state.pop("pending_slot", None)

    if action in ("upgrade", "downgrade") and corrected != original:
        state["reasoning"] = (
            f"{state.get('reasoning') or ''} [Receptionist {action}: {original} → {corrected}]"
        ).strip()
        state["reply"] = ""

    result = invoke_graph(state)
    await memory.save(chat_id, result)

    reply = (result.get("reply") or "").strip()
    if db is not None:
        persist_intake_state(db=db, patient_phone=chat_id, state=result)
        if reply:
            persist_outbound_message(db=db, patient_phone=chat_id, body=reply)
    if reply:
        whatsapp.send_text(chat_id=chat_id, message=reply)

    return result
