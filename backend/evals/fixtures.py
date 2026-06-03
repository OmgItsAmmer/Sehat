"""Labelled messages for classification accuracy evals (Phase 9)."""

from __future__ import annotations

from typing import TypedDict


class EvalCase(TypedDict):
    message: str
    expected: str


# 20 cases — Urdu + English, all four priority levels.
TEST_CASES: list[EvalCase] = [
    # P1 — emergency (5)
    {"message": "seene mein dard ho raha hai", "expected": "P1"},
    {"message": "chest pain since morning", "expected": "P1"},
    {"message": "mere bhai ko saans nahi aa rahi", "expected": "P1"},
    {"message": "unconscious ho gaye hain", "expected": "P1"},
    {"message": "behosh ho gaya hai gir ke", "expected": "P1"},
    # P2 — urgent (5)
    {"message": "bachay ko 3 din se tez bukhaar hai", "expected": "P2"},
    {"message": "suspected fracture in wrist", "expected": "P2"},
    {"message": "severe abdominal pain since last night", "expected": "P2"},
    {"message": "bache ko abhi seizure aa gayi", "expected": "P2"},
    {"message": "bleeding after delivery need doctor urgently", "expected": "P2"},
    # P3 — routine (6)
    {"message": "appointment chahiye back pain ke liye", "expected": "P3"},
    {"message": "follow up visit for diabetes checkup", "expected": "P3"},
    {"message": "mild knee pain, want to book appointment", "expected": "P3"},
    {"message": "skin allergy, dermatology appointment next week", "expected": "P3"},
    {"message": "cough for two weeks, need routine doctor visit", "expected": "P3"},
    {"message": "physiotherapy referral for chronic back pain", "expected": "P3"},
    # OOS — out of scope (4)
    {"message": "fee kitni hai consultation ki", "expected": "OOS"},
    {"message": "visa medical certificate chahiye", "expected": "OOS"},
    {"message": "lab results kab milenge", "expected": "OOS"},
    {"message": "hospital visiting hours kya hain", "expected": "OOS"},
]

PRIORITY_LABELS: dict[str, str] = {
    "P1": "emergency",
    "P2": "urgent",
    "P3": "routine",
    "OOS": "out of scope",
}

PRIORITY_ORDER: tuple[str, ...] = ("P1", "P2", "P3", "OOS")
