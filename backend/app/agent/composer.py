"""LLM-powered reply composer — turns a structured intent into a natural message."""

from __future__ import annotations

import logging

from app.agent.prompts import REPLY_COMPOSER_SYSTEM_PROMPT
from app.config import settings

logger = logging.getLogger(__name__)

_FALLBACK = "Shukriya. Hamari team aap se jald hi rabta karegi."


def compose_reply(
    *,
    last_message: str,
    intent: str,
    filled_slots: dict[str, str] | None = None,
    clinic_context: str = "",
    model: str | None = None,
) -> str:
    """
    Generate a natural patient-facing reply.

    Parameters
    ----------
    last_message : str
        The patient's most recent message — used for language detection.
    intent : str
        Clinical instruction / what the reply must communicate.
    filled_slots : dict | None
        Intake slots already collected (prevents hallucination).
    model : str | None
        Override the default model.

    Returns
    -------
    str
        Natural WhatsApp-ready message text.
    """
    if not settings.openai_api_key:
        logger.warning("compose_reply: OPENAI_API_KEY not set — returning intent as-is")
        return intent or _FALLBACK

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        _model = model or settings.openai_model or "gpt-4o-mini"

        slots_text = (
            "\n".join(f"  {k}: {v}" for k, v in (filled_slots or {}).items()) or "  (none yet)"
        )
        context_block = f"\n\nCLINIC_CONTEXT:\n{clinic_context}" if clinic_context.strip() else ""
        user_content = (
            f"LAST_MESSAGE:\n{last_message}\n\nFILLED_SLOTS:\n{slots_text}"
            f"{context_block}\n\nINTENT:\n{intent}"
        )

        resp = client.chat.completions.create(
            model=_model,
            messages=[
                {"role": "system", "content": REPLY_COMPOSER_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.6,
            max_tokens=200,
        )
        choices = getattr(resp, "choices", None)
        if choices:
            content = getattr(getattr(choices[0], "message", None), "content", None)
            if isinstance(content, str) and content.strip():
                return content.strip()

    except Exception:
        logger.exception("compose_reply: LLM call failed — falling back to intent")

    return intent or _FALLBACK
