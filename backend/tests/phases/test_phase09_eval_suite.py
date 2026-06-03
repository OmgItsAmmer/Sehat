"""Phase 9 — classification eval fixtures and report (no live Gemini in CI)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from app.agent.triage import TriageResult
from evals.fixtures import PRIORITY_ORDER, TEST_CASES
from evals.test_classification import (
    EvalResult,
    classify_for_eval,
    format_classification_report,
    run_classification_eval,
)

pytestmark = [pytest.mark.unit, pytest.mark.phase9]


def test_fixtures_cover_twenty_labelled_messages() -> None:
    assert len(TEST_CASES) == 20
    for case in TEST_CASES:
        assert case["expected"] in PRIORITY_ORDER


def test_classify_for_eval_p1_keyword_without_gemini() -> None:
    with patch("app.agent.nodes.classify_message_with_gemini") as mock_gemini:
        out = classify_for_eval("seene mein dard ho raha hai")
    mock_gemini.assert_not_called()
    assert out["priority"] == "P1"


@patch("app.agent.nodes.classify_message_with_gemini")
def test_eval_suite_perfect_classifier_scores_100_percent(mock_classify) -> None:
    def _fake_classify(message: str) -> TriageResult:
        for case in TEST_CASES:
            if case["message"] == message:
                return TriageResult(
                    priority=case["expected"],
                    confidence=0.92,
                    reasoning="Eval mock.",
                )
        raise AssertionError(f"unexpected eval message: {message!r}")

    mock_classify.side_effect = _fake_classify

    results = run_classification_eval()
    assert len(results) == 20
    assert all(r.correct for r in results)

    report = format_classification_report(results)
    assert "Overall" in report
    assert "20/20" in report


def test_format_report_shows_per_priority_buckets() -> None:
    results = [
        EvalResult("a", "P1", "P1", 1.0, ""),
        EvalResult("b", "P2", "P2", 0.8, ""),
    ]
    report = format_classification_report(results)
    assert "P1  (emergency)" in report
    assert "P2  (urgent)" in report
