"""Pick which specialist handles slot-filling for this thread."""

from __future__ import annotations

from app.agent.state import TriageState


def pick_specialist(state: TriageState) -> str:
    """
    Route by triage priority and message keywords.

    Cardiology wins over pediatrics when both could match (e.g. chest pain in a child).
    """
    text = " ".join(state.get("messages") or []).lower()
    priority = state.get("priority")

    if priority == "P1" or any(
        k in text for k in ("seene", "chest", "dil", "heart", "cardiac")
    ):
        return "cardiology"
    if any(k in text for k in ("bach", "bachay", "child", "infant", "baby", "pediatric")):
        return "pediatrics"
    return "general"
