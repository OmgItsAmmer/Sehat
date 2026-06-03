"""Human-in-the-loop priority overrides — audit log + pipeline resume."""

from __future__ import annotations

from typing import Any, Literal

from sqlalchemy.orm import Session

from app.models.override import Override
from app.services.pipeline import OverrideAction, resume_after_override

OverrideActionType = Literal["agree", "upgrade", "downgrade"]


def save_override_record(
    *,
    db: Session,
    patient_phone: str,
    original_priority: str | None,
    corrected_priority: str | None,
    action: OverrideActionType,
    receptionist_id: str,
) -> Override:
    row = Override(
        patient_phone=patient_phone,
        original_priority=original_priority,
        corrected_priority=corrected_priority,
        action=action,
        receptionist_id=receptionist_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


async def apply_override(
    *,
    patient_phone: str,
    action: OverrideAction,
    receptionist_id: str,
    db: Session | None,
) -> dict[str, Any]:
    from app.services import memory

    before = await memory.load(patient_phone)
    original = before.get("priority")

    result = await resume_after_override(
        chat_id=patient_phone,
        action=action,
        receptionist_id=receptionist_id,
        db=db,
    )

    if db is not None:
        save_override_record(
            db=db,
            patient_phone=patient_phone,
            original_priority=original,
            corrected_priority=result.get("priority"),
            action=action,
            receptionist_id=receptionist_id,
        )

    return {
        "status": "resumed",
        "phone": patient_phone,
        "original_priority": original,
        "priority": result.get("priority"),
        "action": action,
        "reply": result.get("reply"),
        "awaiting_human_review": result.get("awaiting_human_review"),
        "escalated": result.get("escalated"),
    }
