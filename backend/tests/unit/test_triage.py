"""Phase 3 unit tests: OpenAI triage classification (mocked — no live API in CI)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from app.agent.triage import (
    OpenAITriageConfig,
    TriageResult,
    classify_message_with_openai,
)
from pydantic import ValidationError

pytestmark = pytest.mark.unit


@pytest.fixture
def openai_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.agent.triage.settings.openai_api_key", "test-key")
    monkeypatch.setattr("app.agent.triage.settings.openai_model", "gpt-4o-mini")


def _mock_openai_response(payload: dict) -> MagicMock:
    choice = MagicMock()
    choice.message.content = json.dumps(payload)
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@patch("openai.OpenAI")
def test_classify_returns_p1_for_chest_pain(
    mock_client_cls: MagicMock,
    openai_api_key: None,
) -> None:
    mock_client = mock_client_cls.return_value
    mock_client.chat.completions.create.return_value = _mock_openai_response(
        {
            "priority": "P1",
            "confidence": 0.96,
            "reasoning": "Chest pain may indicate cardiac emergency.",
        }
    )

    result = classify_message_with_openai("seene mein dard ho raha hai")

    assert result.priority == "P1"
    assert result.confidence == 0.96
    assert "chest" in result.reasoning.lower() or "cardiac" in result.reasoning.lower()

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-4o-mini"
    assert call_kwargs["messages"][-1]["content"] == "seene mein dard ho raha hai"


@patch("openai.OpenAI")
def test_classify_uses_config_model_override(
    mock_client_cls: MagicMock,
    openai_api_key: None,
) -> None:
    mock_client = mock_client_cls.return_value
    mock_client.chat.completions.create.return_value = _mock_openai_response(
        {"priority": "P3", "confidence": 0.8, "reasoning": "Routine appointment request."}
    )

    classify_message_with_openai(
        "appointment chahiye",
        cfg=OpenAITriageConfig(model="gpt-4.1-mini"),
    )

    assert mock_client.chat.completions.create.call_args.kwargs["model"] == "gpt-4.1-mini"


def test_classify_raises_when_api_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.agent.triage.settings.openai_api_key", "")

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is not configured"):
        classify_message_with_openai("hello")


@patch("openai.OpenAI")
def test_classify_raises_on_empty_response(
    mock_client_cls: MagicMock,
    openai_api_key: None,
) -> None:
    mock_client = mock_client_cls.return_value
    mock_client.chat.completions.create.return_value = MagicMock(choices=[])

    with pytest.raises(RuntimeError, match="empty response"):
        classify_message_with_openai("hello")


@patch("openai.OpenAI")
def test_classify_raises_on_invalid_json(
    mock_client_cls: MagicMock,
    openai_api_key: None,
) -> None:
    mock_client = mock_client_cls.return_value
    choice = MagicMock()
    choice.message.content = "not json"
    mock_client.chat.completions.create.return_value = MagicMock(choices=[choice])

    with pytest.raises(json.JSONDecodeError):
        classify_message_with_openai("hello")


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
