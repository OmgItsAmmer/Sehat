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
class GeminiTriageConfig:
    # Not "gemini-3.0-flash" — that id does not exist on the API.
    model: str = "gemini-3-flash-preview"


def _gemini_response_text(resp: object) -> str | None:
    """Extract JSON text from a generate_content response."""
    text = getattr(resp, "text", None)
    if isinstance(text, str) and text:
        return text

    candidates = getattr(resp, "candidates", None)
    if not candidates:
        return None
    try:
        first = candidates[0]
        content = getattr(first, "content", None)
        parts = getattr(content, "parts", None) if content is not None else None
        if not parts:
            return None
        part_text = getattr(parts[0], "text", None)
        return part_text if isinstance(part_text, str) else None
    except (IndexError, TypeError):
        return None


def classify_message_with_gemini(
    message: str,
    *,
    cfg: GeminiTriageConfig | None = None,
) -> TriageResult:
    """
    Phase 3 scratch-call: one Gemini request returning structured triage JSON.
    """
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    model = (cfg.model if cfg else settings.gemini_model) or GeminiTriageConfig.model

    # Import lazily so tests don't require the dependency.
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)

    prompt = f"{TRIAGE_SYSTEM_PROMPT}\n\nMessage: {message}"
    resp = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )

    text = _gemini_response_text(resp)
    if not text:
        raise RuntimeError("Gemini returned an empty response")

    data = json.loads(text)
    return TriageResult.model_validate(data)
