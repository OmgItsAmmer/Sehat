"""Receptionist priority override — agree / upgrade / downgrade."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services import memory
from app.services.override import apply_override

router = APIRouter(prefix="/api", tags=["override"])


class OverrideRequest(BaseModel):
    action: Literal["agree", "upgrade", "downgrade"]
    receptionist_id: str = Field(default="receptionist", min_length=1, max_length=64)


@router.post("/cases/{phone:path}/override")
async def override_case(
    phone: str,
    body: OverrideRequest,
    db: Annotated[Session | None, Depends(get_db)],
) -> dict[str, Any]:
    """
    Log correction, update session priority, resume graph, reply to patient.
    """
    state = await memory.load(phone)
    if not state.get("messages"):
        raise HTTPException(status_code=404, detail="Case not found")

    if not state.get("awaiting_human_review") and not state.get("escalated"):
        raise HTTPException(
            status_code=400,
            detail="Case is not awaiting human review",
        )

    try:
        return await apply_override(
            patient_phone=phone,
            action=body.action,
            receptionist_id=body.receptionist_id,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
