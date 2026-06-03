"""Unified intake pipeline — memory (6), dashboard review (7), specialists (8)."""

from __future__ import annotations

import logging
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.agent.graph import invoke_graph
from app.agent.state import TriageState, latest_message, merge_state
from app.services import memory, whatsapp
from app.services.persist import persist_incoming_message, persist_outbound_message

logger = logging.getLogger(__name__)

OverrideAction = Literal["agree", "upgrade", "downgrade"]

_UPGRADE: dict[str, str] = {"OOS": "P3", "P3": "P2", "P2": "P1", "P1": "P1"}
_DOWNGRADE: dict[str, str] = {"P1": "P2", "P2": "P3", "P3": "OOS", "OOS": "OOS"}

HOLD_REPLY = "Your case is with our reception team. We will message you again shortly."


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


async def process_inbound(
    *,
    chat_id: str,
    body: str,
    db: Session | None = None,
    raw_payload: dict[str, Any] | None = None,
) -> TriageState:
    """Load session → run graph → save → persist → WhatsApp reply."""
    state = await memory.load(chat_id)
    messages = list(state.get("messages") or [])
    messages.append(body)
    state["messages"] = messages
    state["patient_phone"] = chat_id

    if state.get("awaiting_human_review"):
        state["reply"] = HOLD_REPLY
        await memory.save(chat_id, state)
        if db is not None:
            persist_incoming_message(
                db=db,
                patient_phone=chat_id,
                body=body,
                raw_payload=raw_payload,
            )
            persist_outbound_message(db=db, patient_phone=chat_id, body=HOLD_REPLY)
        whatsapp.send_text(chat_id=chat_id, message=HOLD_REPLY)
        return state

    slot_patch = apply_pending_slot_answer(state)
    if slot_patch:
        state = merge_state(state, slot_patch)

    result = invoke_graph(state)
    await memory.save(chat_id, result)

    if db is not None:
        persist_incoming_message(
            db=db,
            patient_phone=chat_id,
            body=body,
            raw_payload=raw_payload,
        )
        reply = (result.get("reply") or "").strip()
        if reply:
            persist_outbound_message(db=db, patient_phone=chat_id, body=reply)

    reply = (result.get("reply") or "").strip()
    if reply:
        whatsapp.send_text(chat_id=chat_id, message=reply)

    return result


async def resume_after_override(
    *,
    chat_id: str,
    action: OverrideAction,
    receptionist_id: str,
    db: Session | None = None,
) -> TriageState:
    """Apply receptionist decision, re-run graph, notify patient."""
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
    if db is not None and reply:
        persist_outbound_message(db=db, patient_phone=chat_id, body=reply)
    if reply:
        whatsapp.send_text(chat_id=chat_id, message=reply)

    return result
