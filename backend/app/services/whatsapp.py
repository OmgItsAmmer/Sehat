"""Green API client — send outbound WhatsApp text."""

from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

GREEN_API_BASE = "https://api.greenapi.com"
SEND_TIMEOUT_SECONDS = 15.0


def is_configured() -> bool:
    return bool(settings.green_api_instance and settings.green_api_token)


def send_text(*, chat_id: str, message: str) -> bool:
    """
    Send a text message via Green API SendMessage.

    Returns True when credentials are set and the API accepts the message.
    """
    if not message.strip():
        return False

    if not is_configured():
        logger.warning("Green API not configured — would send to %s: %s", chat_id, message[:80])
        return False

    url = (
        f"{GREEN_API_BASE}/waInstance{settings.green_api_instance}"
        f"/sendMessage/{settings.green_api_token}"
    )
    payload = {"chatId": chat_id, "message": message}

    try:
        with httpx.Client(timeout=SEND_TIMEOUT_SECONDS) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
    except httpx.HTTPError:
        logger.exception("Green API sendMessage failed chat_id=%s", chat_id)
        return False

    logger.info("WhatsApp reply sent chat_id=%s len=%d", chat_id, len(message))
    return True
