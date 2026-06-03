"""Registry of specialist profiles used by slot_check and gather_slots."""

from __future__ import annotations

from dataclasses import dataclass

from app.agent.specialists import cardiology, general, pediatrics

DEFAULT_SPECIALIST = "general"


@dataclass(frozen=True)
class SpecialistProfile:
    key: str
    system_prompt: str
    required_slots: tuple[str, ...]
    slot_questions: dict[str, str]


_PROFILES: dict[str, SpecialistProfile] = {
    "general": SpecialistProfile(
        key="general",
        system_prompt=general.SYSTEM_PROMPT.strip(),
        required_slots=general.REQUIRED_SLOTS,
        slot_questions=general.SLOT_QUESTIONS,
    ),
    "cardiology": SpecialistProfile(
        key="cardiology",
        system_prompt=cardiology.SYSTEM_PROMPT.strip(),
        required_slots=cardiology.REQUIRED_SLOTS,
        slot_questions=cardiology.SLOT_QUESTIONS,
    ),
    "pediatrics": SpecialistProfile(
        key="pediatrics",
        system_prompt=pediatrics.SYSTEM_PROMPT.strip(),
        required_slots=pediatrics.REQUIRED_SLOTS,
        slot_questions=pediatrics.SLOT_QUESTIONS,
    ),
}


def get_profile(specialist_key: str | None) -> SpecialistProfile:
    if not specialist_key:
        return _PROFILES[DEFAULT_SPECIALIST]
    return _PROFILES.get(specialist_key, _PROFILES[DEFAULT_SPECIALIST])
