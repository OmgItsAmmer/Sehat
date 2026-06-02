"""Orchestrate webhook → memory → graph → outbound reply."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.agent.graph import graph
from app.agent.state import TriageState, latest_message
from app.services import memory, whatsapp
from app.services.persist import persist_incoming_message

logger = logging.getLogger(__name__)


def apply_pending_slot_answer(state: TriageState) -> dict[str, Any]:
    """
    When the bot asked a slot question, store the patient's new message in `slots`.
    """
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


async def process_incoming_message(
    *,
    chat_id: str,
    body: str,
    db: Session | None = None,
    raw_payload: dict[str, Any] | None = None,
) -> TriageState:
    """Load session, run triage graph, save state, optionally persist and reply."""
    state = await memory.load(chat_id)
    messages = list(state.get("messages") or [])
    messages.append(body)
    state["messages"] = messages
    state["patient_phone"] = chat_id

    slot_patch = apply_pending_slot_answer(state)
    if slot_patch:
        state.update(slot_patch)  # type: ignore[typeddict-unknown-key]

    result: TriageState = graph.invoke(state)
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
        whatsapp.send_text(chat_id=chat_id, message=reply)

    return result
