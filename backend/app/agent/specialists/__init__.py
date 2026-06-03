"""Specialist intake profiles — prompts and slot schemas per department."""

from app.agent.specialists.registry import SpecialistProfile, get_profile

__all__ = ["SpecialistProfile", "get_profile"]
