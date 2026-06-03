"""Phase 3 — single OpenAI classify call returns structured triage JSON."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from app.agent.prompts import TRIAGE_SYSTEM_PROMPT
from app.agent.triage import TriageResult, classify_message_with_openai

pytestmark = [pytest.mark.unit, pytest.mark.phase3]


@pytest.fixture
def openai_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.agent.triage.settings.openai_api_key", "test-key")


def test_triage_prompt_defines_all_priorities() -> None:
    for label in ("P1", "P2", "P3", "OOS"):
        assert label in TRIAGE_SYSTEM_PROMPT


@patch("openai.OpenAI")
def test_classify_returns_structured_p1(
    mock_client_cls: MagicMock,
    openai_api_key: None,
) -> None:
    choice = MagicMock()
    choice.message.content = json.dumps(
        {
            "priority": "P1",
            "confidence": 0.96,
            "reasoning": "Chest pain emergency.",
        }
    )
    mock_client = mock_client_cls.return_value
    mock_client.chat.completions.create.return_value = MagicMock(choices=[choice])

    result = classify_message_with_openai("chest pain since morning")

    assert isinstance(result, TriageResult)
    assert result.priority == "P1"
    assert 0.0 <= result.confidence <= 1.0
