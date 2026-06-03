"""Phase 9 — run labelled messages through classify_node and print accuracy."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

# `python -m evals.test_classification` from backend/ does not add backend to sys.path.
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.agent.nodes import classify_node
from app.agent.state import TriageState
from app.config import settings
from evals.fixtures import PRIORITY_LABELS, PRIORITY_ORDER, TEST_CASES, EvalCase


@dataclass(frozen=True)
class EvalResult:
    message: str
    expected: str
    predicted: str
    confidence: float
    reasoning: str

    @property
    def correct(self) -> bool:
        return self.predicted == self.expected


def classify_for_eval(message: str) -> dict:
    """Single-message classify_node invocation (same path as production graph)."""
    state: TriageState = {
        "messages": [message],
        "patient_phone": "eval",
        "confidence": 0.0,
        "clarification_rounds": 0,
    }
    return classify_node(state)


def run_classification_eval(
    cases: list[EvalCase] | None = None,
) -> list[EvalResult]:
    rows: list[EvalResult] = []
    for case in cases or TEST_CASES:
        out = classify_for_eval(case["message"])
        rows.append(
            EvalResult(
                message=case["message"],
                expected=case["expected"],
                predicted=out.get("priority") or "?",
                confidence=float(out.get("confidence") or 0.0),
                reasoning=str(out.get("reasoning") or ""),
            )
        )
    return rows


def format_classification_report(results: list[EvalResult]) -> str:
    """Human-readable accuracy table (matches plan.md Phase 9 example)."""
    lines = ["Classification accuracy report", "─" * 32]

    total_correct = 0
    confidences: list[float] = []

    for priority in PRIORITY_ORDER:
        bucket = [r for r in results if r.expected == priority]
        if not bucket:
            continue
        correct = sum(1 for r in bucket if r.correct)
        total = len(bucket)
        total_correct += correct
        pct = (100 * correct / total) if total else 0.0
        label = PRIORITY_LABELS.get(priority, priority)
        lines.append(
            f"{priority}  ({label})".ljust(22)
            + f"{correct}/{total}".rjust(6)
            + f"{pct:6.0f}%".rjust(8)
        )
        confidences.extend(r.confidence for r in bucket)

    overall_total = len(results)
    overall_pct = (100 * total_correct / overall_total) if overall_total else 0.0
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

    lines.append("─" * 32)
    lines.append(
        "Overall".ljust(22)
        + f"{total_correct}/{overall_total}".rjust(6)
        + f"{overall_pct:6.0f}%".rjust(8)
    )
    lines.append(f"Avg confidence     {avg_conf:.2f}")
    return "\n".join(lines)


def _print_misclassified(results: list[EvalResult]) -> None:
    wrong = [r for r in results if not r.correct]
    if not wrong:
        return
    print("\nMisclassified:")
    for r in wrong:
        print(f"  expected {r.expected}, got {r.predicted} — {r.message!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Triage classification eval (Phase 9)")
    parser.add_argument(
        "--show-errors",
        action="store_true",
        help="List messages where predicted priority != expected",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if any case is misclassified",
    )
    args = parser.parse_args(argv)

    if not settings.gemini_api_key:
        print(
            "GEMINI_API_KEY is not set. Eval needs Gemini for non–P1-keyword cases.",
            file=sys.stderr,
        )
        return 1

    results = run_classification_eval()
    print(format_classification_report(results))
    if args.show_errors:
        _print_misclassified(results)

    if args.strict and any(not r.correct for r in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
