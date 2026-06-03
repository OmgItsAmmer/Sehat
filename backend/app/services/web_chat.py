"""Web chat channel — session helpers and API response shaping."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.agent.state import TriageState, latest_message
from app.channels import WEB_SESSION_ID_PREFIX
from app.services import web_memory
from app.services.pipeline import process_web_inbound

_SESSION_ID_RE = re.compile(rf"^{re.escape(WEB_SESSION_ID_PREFIX)}[0-9a-fA-F-]{{8,}}$")


def is_valid_session_id(session_id: str) -> bool:
    return bool(_SESSION_ID_RE.match(session_id.strip()))


def state_to_session_payload(session_id: str, state: TriageState) -> dict[str, Any]:
    messages = list(state.get("messages") or [])
    return {
        "session_id": session_id,
        "channel": "web",
        "priority": state.get("priority"),
        "confidence": state.get("confidence") or 0.0,
        "reasoning": state.get("reasoning") or "",
        "escalated": bool(state.get("escalated")),
        "slots_complete": bool(state.get("slots_complete")),
        "slots": state.get("slots") or {},
        "routed_to": state.get("routed_to"),
        "message_count": len(messages),
        "last_message": latest_message(state),
        "pending_slot": state.get("pending_slot"),
        "reply": state.get("reply") or "",
        "awaiting_human_review": bool(state.get("awaiting_human_review")),
        "messages": messages,
        "clarification_rounds": state.get("clarification_rounds") or 0,
    }


async def get_session(session_id: str) -> dict[str, Any]:
    """Return web session state (empty shell when no messages yet — not 404)."""
    if not is_valid_session_id(session_id):
        raise ValueError("Invalid web session id")
    state = await web_memory.load(session_id)
    return state_to_session_payload(session_id, state)


async def post_message(
    *,
    session_id: str,
    body: str,
    db: Session | None = None,
) -> dict[str, Any]:
    if not is_valid_session_id(session_id):
        raise ValueError("Invalid web session id")
    result = await process_web_inbound(session_id=session_id, body=body, db=db)
    payload = state_to_session_payload(session_id, result)
    payload["reply"] = (result.get("reply") or "").strip()
    return payload
