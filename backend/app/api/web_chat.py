"""REST API for the web patient chat channel (separate from WhatsApp / clinic cases)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.channels import WEB_SESSION_ID_PREFIX
from app.database.session import get_db
from app.services import web_chat

router = APIRouter(prefix="/api/web-chat", tags=["web-chat"])


class WebChatMessageIn(BaseModel):
    session_id: str = Field(
        ...,
        min_length=12,
        description=f"Web session id, e.g. {WEB_SESSION_ID_PREFIX}<uuid>",
    )
    body: str = Field(..., min_length=1, max_length=4096)


@router.get("/sessions/{session_id}")
async def get_web_session(session_id: str) -> dict[str, Any]:
    """Load web chat history. Returns an empty session (200) when nothing stored yet."""
    try:
        return await web_chat.get_session(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/message")
async def post_web_message(
    body: WebChatMessageIn,
    db: Annotated[Session | None, Depends(get_db)],
) -> dict[str, Any]:
    """Process one inbound web chat turn; bot reply is in the JSON body (no WhatsApp send)."""
    try:
        return await web_chat.post_message(session_id=body.session_id, body=body.body, db=db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
