"""Slack incoming-webhook alerts for urgent triage cases."""

from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

SLACK_TIMEOUT_SECONDS = 4.0


def send_triage_alert(
    *,
    patient_phone: str,
    priority: str,
    routed_to: str | None,
    reasoning: str,
    message_preview: str,
    escalated: bool,
) -> bool:
    """
    Post a P1/escalation alert to Slack.

    Returns True when a webhook was configured and the request succeeded.
    """
    if not settings.slack_webhook_url:
        logger.warning(
            "SLACK_WEBHOOK_URL not set — skipping alert phone=%s priority=%s",
            patient_phone,
            priority,
        )
        return False

    text = (
        f":rotating_light: *Sehat triage alert*\n"
        f"*Priority:* {priority}\n"
        f"*Phone:* {patient_phone}\n"
        f"*Routed to:* {routed_to or 'n/a'}\n"
        f"*Escalated:* {escalated}\n"
        f"*Reasoning:* {reasoning or '—'}\n"
        f"*Latest message:* {message_preview[:500]}"
    )
    payload = {"text": text}

    try:
        with httpx.Client(timeout=SLACK_TIMEOUT_SECONDS) as client:
            response = client.post(settings.slack_webhook_url, json=payload)
            response.raise_for_status()
    except httpx.HTTPError:
        logger.exception("Slack triage alert failed phone=%s priority=%s", patient_phone, priority)
        return False

    logger.info("Slack triage alert sent phone=%s priority=%s", patient_phone, priority)
    return True
