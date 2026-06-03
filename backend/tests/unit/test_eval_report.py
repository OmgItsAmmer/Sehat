"""Unit tests for Phase 9 eval report formatting (no live OpenAI)."""

from __future__ import annotations

import pytest
from evals.test_classification import EvalResult, format_classification_report

pytestmark = pytest.mark.unit


def test_format_classification_report_layout() -> None:
    results = [
        EvalResult("a", "P1", "P1", 1.0, ""),
        EvalResult("b", "P1", "P2", 0.5, ""),
        EvalResult("c", "P3", "P3", 0.9, ""),
        EvalResult("d", "OOS", "OOS", 0.95, ""),
    ]
    report = format_classification_report(results)

    assert "Classification accuracy report" in report
    assert "P1  (emergency)" in report
    assert "1/2" in report
    assert "Overall" in report
    assert "3/4" in report
    assert "Avg confidence" in report
