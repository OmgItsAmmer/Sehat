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


def classify_message_with_gemini(message: str, *, cfg: GeminiTriageConfig | None = None) -> TriageResult:
    """
    Phase 3 scratch-call: one Gemini request returning structured triage JSON.
    """
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    model = (cfg.model if cfg else settings.gemini_model) or GeminiTriageConfig.model

    # Import lazily so tests don't require the dependency.
    from google import genai  # type: ignore
    from google.genai import types  # type: ignore

    client = genai.Client(api_key=settings.gemini_api_key)

    prompt = f"{TRIAGE_SYSTEM_PROMPT}\n\nMessage: {message}"
    resp = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )

    # The SDK returns a rich object; extract raw text defensively.
    text: str | None = None
    if hasattr(resp, "text"):
        text = resp.text  # type: ignore[assignment]
    if not text and hasattr(resp, "candidates"):
        try:
            text = resp.candidates[0].content.parts[0].text  # type: ignore[attr-defined]
        except Exception:
            text = None

    if not text:
        raise RuntimeError("Gemini returned an empty response")

    data = json.loads(text)
    return TriageResult.model_validate(data)

