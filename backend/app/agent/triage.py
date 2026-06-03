from __future__ import annotations

import json
from dataclasses import dataclass

from pydantic import BaseModel, Field

from app.agent.prompts import TRIAGE_SYSTEM_PROMPT
from app.config import settings


class TriageResult(BaseModel):
    priority: str = Field(pattern="^(P1|P2|P3|OOS)$")
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


@dataclass(frozen=True)
class OpenAITriageConfig:
    model: str = "gpt-4o-mini"


def _openai_response_text(resp: object) -> str | None:
    """Extract JSON text from a chat completion response."""
    try:
        choices = getattr(resp, "choices", None)
        if not choices:
            return None
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None) if message is not None else None
        return content if isinstance(content, str) and content else None
    except (IndexError, TypeError):
        return None


def classify_message_with_openai(
    message: str,
    *,
    cfg: OpenAITriageConfig | None = None,
) -> TriageResult:
    """
    Phase 3 scratch-call: one OpenAI request returning structured triage JSON.
    """
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    model = (cfg.model if cfg else settings.openai_model) or OpenAITriageConfig.model

    # Import lazily so tests don't require the dependency.
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
        response_format={"type": "json_object"},
    )

    text = _openai_response_text(resp)
    if not text:
        raise RuntimeError("OpenAI returned an empty response")

    data = json.loads(text)
    return TriageResult.model_validate(data)
