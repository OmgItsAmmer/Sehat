"""WhatsApp webhook intake — clinic channel only."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.agent.state import TriageState
from app.services.pipeline import apply_pending_slot_answer, process_whatsapp_inbound

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
    return await process_whatsapp_inbound(
        chat_id=chat_id,
        body=body,
        db=db,
        raw_payload=raw_payload,
    )
