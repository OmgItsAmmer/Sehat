"""Webhook intake — delegates to the unified pipeline."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.agent.state import TriageState
from app.services.pipeline import apply_pending_slot_answer, process_inbound

__all__ = [
    "apply_pending_slot_answer",
    "process_incoming_message",
]


async def process_incoming_message(
    *,
    chat_id: str,
    body: str,
    db: Session | None = None,
    raw_payload: dict[str, Any] | None = None,
) -> TriageState:
    return await process_inbound(
        chat_id=chat_id,
        body=body,
        db=db,
        raw_payload=raw_payload,
    )
