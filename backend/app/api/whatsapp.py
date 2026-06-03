"""Green API webhook receiver — incoming WhatsApp messages."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.intake import process_incoming_message

router = APIRouter()
console = logging.getLogger("uvicorn.error")


def _as_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _extract_message_body(message_data: dict[str, Any]) -> str | None:
    """Pull human-readable text from Green API messageData (varies by typeMessage)."""
    type_message = message_data.get("typeMessage")

    if type_message == "textMessage":
        return _as_str(message_data.get("textMessageData", {}).get("textMessage"))

    if type_message == "extendedTextMessage":
        return _as_str(message_data.get("extendedTextMessageData", {}).get("text"))

    if type_message == "quotedMessage":
        ext = message_data.get("extendedTextMessageData", {})
        return _as_str(ext.get("text"))

    if type_message in ("imageMessage", "videoMessage", "documentMessage", "audioMessage"):
        caption = _as_str(message_data.get("fileMessageData", {}).get("caption"))
        if caption:
            return caption
        return f"[{type_message}]"

    if type_message == "interactiveButtonsReply":
        reply = message_data.get("interactiveButtonsReply", {})
        return _as_str(reply.get("contentText")) or _as_str(reply.get("titleText"))

    return None


def _format_incoming_log(payload: dict[str, Any]) -> str:
    webhook_type = payload.get("typeWebhook", "unknown")
    sender = payload.get("senderData") or {}
    chat_id = sender.get("chatId", "?")
    sender_name = sender.get("senderName") or sender.get("senderContactName") or "?"

    message_data = payload.get("messageData") or {}
    body = _extract_message_body(message_data) if message_data else None

    lines = [
        "",
        "--- WhatsApp (Green API) ---",
        f"  webhook : {webhook_type}",
        f"  from    : {sender_name} ({chat_id})",
    ]
    if body:
        lines.append(f"  message : {body}")
    elif message_data:
        lines.append(f"  message : [{message_data.get('typeMessage', 'no text')}]")
    lines.append("----------------------------")
    return "\n".join(lines)


@router.post("/webhook")
async def green_api_webhook(
    request: Request,
    db: Annotated[Session | None, Depends(get_db)],
) -> dict[str, bool | str]:
    """
    Green API POSTs every instance event here (Webhook Endpoint technology).

    For incoming patient messages, typeWebhook is ``incomingMessageReceived``.
    Must return HTTP 200 so Green API clears the notification from its queue.
    """
    payload: dict[str, Any] = await request.json()

    log_block = _format_incoming_log(payload)
    for line in log_block.splitlines():
        if line.strip():
            console.info(line)

    if payload.get("typeWebhook") == "incomingMessageReceived":
        sender = payload.get("senderData") or {}
        chat_id = sender.get("chatId")
        message_data = payload.get("messageData") or {}
        body = _extract_message_body(message_data) if message_data else None

        if isinstance(chat_id, str) and body:
            result = await process_incoming_message(
                chat_id=chat_id,
                body=body,
                db=db,
                raw_payload=payload,
            )
            priority = result.get("priority")
            if priority:
                console.info(
                    "  triage  : priority=%s reply_sent=%s",
                    priority,
                    bool(result.get("reply")),
                )

    elif payload.get("typeWebhook") != "incomingMessageReceived":
        console.info("(non-message webhook — see Green API dashboard for full payload)")

    return {"ok": True}
