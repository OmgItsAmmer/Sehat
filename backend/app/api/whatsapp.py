"""Green API webhook receiver — incoming WhatsApp messages."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Request

router = APIRouter()
# uvicorn.error always prints in the same terminal as "Uvicorn running on ..."
console = logging.getLogger("uvicorn.error")


def _extract_message_body(message_data: dict[str, Any]) -> str | None:
    """Pull human-readable text from Green API messageData (varies by typeMessage)."""
    type_message = message_data.get("typeMessage")

    if type_message == "textMessage":
        return message_data.get("textMessageData", {}).get("textMessage")

    if type_message == "extendedTextMessage":
        return message_data.get("extendedTextMessageData", {}).get("text")

    if type_message == "quotedMessage":
        ext = message_data.get("extendedTextMessageData", {})
        return ext.get("text")

    if type_message in ("imageMessage", "videoMessage", "documentMessage", "audioMessage"):
        caption = message_data.get("fileMessageData", {}).get("caption")
        if caption:
            return caption
        return f"[{type_message}]"

    if type_message == "interactiveButtonsReply":
        reply = message_data.get("interactiveButtonsReply", {})
        return reply.get("contentText") or reply.get("titleText")

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
async def green_api_webhook(request: Request) -> dict[str, bool]:
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

    if payload.get("typeWebhook") != "incomingMessageReceived":
        console.info("(non-message webhook — see Green API dashboard for full payload)")

    return {"ok": True}
