"""Phase 3 unit tests: Gemini triage classification (mocked — no live API in CI)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from app.agent.triage import (
    GeminiTriageConfig,
    TriageResult,
    classify_message_with_gemini,
)
from pydantic import ValidationError

pytestmark = pytest.mark.unit


@pytest.fixture
def gemini_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.agent.triage.settings.gemini_api_key", "test-key")
    monkeypatch.setattr("app.agent.triage.settings.gemini_model", "gemini-3-flash-preview")


def _mock_gemini_response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.text = json.dumps(payload)
    return resp


@patch("google.genai.Client")
def test_classify_returns_p1_for_chest_pain(
    mock_client_cls: MagicMock,
    gemini_api_key: None,
) -> None:
    mock_client = mock_client_cls.return_value
    mock_client.models.generate_content.return_value = _mock_gemini_response(
        {
            "priority": "P1",
            "confidence": 0.96,
            "reasoning": "Chest pain may indicate cardiac emergency.",
        }
    )

    result = classify_message_with_gemini("seene mein dard ho raha hai")

    assert result.priority == "P1"
    assert result.confidence == 0.96
    assert "chest" in result.reasoning.lower() or "cardiac" in result.reasoning.lower()

    call_kwargs = mock_client.models.generate_content.call_args.kwargs
    assert call_kwargs["model"] == "gemini-3-flash-preview"
    assert "seene mein dard" in call_kwargs["contents"]


@patch("google.genai.Client")
def test_classify_uses_config_model_override(
    mock_client_cls: MagicMock,
    gemini_api_key: None,
) -> None:
    mock_client = mock_client_cls.return_value
    mock_client.models.generate_content.return_value = _mock_gemini_response(
        {"priority": "P3", "confidence": 0.8, "reasoning": "Routine appointment request."}
    )

    classify_message_with_gemini(
        "appointment chahiye",
        cfg=GeminiTriageConfig(model="gemini-3.5-flash"),
    )

    assert mock_client.models.generate_content.call_args.kwargs["model"] == "gemini-3.5-flash"


def test_classify_raises_when_api_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.agent.triage.settings.gemini_api_key", "")

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY is not configured"):
        classify_message_with_gemini("hello")


@patch("google.genai.Client")
def test_classify_raises_on_empty_response(
    mock_client_cls: MagicMock,
    gemini_api_key: None,
) -> None:
    mock_client = mock_client_cls.return_value
    mock_client.models.generate_content.return_value = MagicMock(text=None, candidates=[])

    with pytest.raises(RuntimeError, match="empty response"):
        classify_message_with_gemini("hello")


@patch("google.genai.Client")
def test_classify_raises_on_invalid_json(
    mock_client_cls: MagicMock,
    gemini_api_key: None,
) -> None:
    mock_client = mock_client_cls.return_value
    mock_client.models.generate_content.return_value = MagicMock(text="not json")

    with pytest.raises(json.JSONDecodeError):
        classify_message_with_gemini("hello")


@pytest.mark.parametrize(
    ("payload", "expected_priority"),
    [
        ({"priority": "P1", "confidence": 1.0, "reasoning": "Emergency."}, "P1"),
        ({"priority": "P2", "confidence": 0.85, "reasoning": "Urgent."}, "P2"),
        ({"priority": "P3", "confidence": 0.7, "reasoning": "Routine."}, "P3"),
        ({"priority": "OOS", "confidence": 0.9, "reasoning": "Billing question."}, "OOS"),
    ],
)
def test_triage_result_accepts_valid_priorities(payload: dict, expected_priority: str) -> None:
    result = TriageResult.model_validate(payload)
    assert result.priority == expected_priority


@pytest.mark.parametrize(
    "payload",
    [
        {"priority": "P4", "confidence": 0.5, "reasoning": "Invalid priority."},
        {"priority": "P1", "confidence": 1.5, "reasoning": "Confidence too high."},
        {"priority": "P1", "confidence": -0.1, "reasoning": "Confidence too low."},
    ],
)
def test_triage_result_rejects_invalid_payload(payload: dict) -> None:
    with pytest.raises(ValidationError):
        TriageResult.model_validate(payload)
