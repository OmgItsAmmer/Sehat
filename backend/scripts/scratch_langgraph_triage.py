from __future__ import annotations

import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.agent.graph import graph


def main() -> None:
    result = graph.invoke(
        {
            "messages": ["seene mein dard"],
            "patient_phone": "+923001234567",
            "priority": None,
            "confidence": 0.0,
            "clarification_rounds": 0,
            "slots": {},
            "slots_complete": False,
            "routed_to": None,
            "escalated": False,
            "slack_notified": False,
            "reply": "",
        }
    )

    print("priority:", result.get("priority"))
    print("escalated:", result.get("escalated"))
    print("slack_notified:", result.get("slack_notified"))
    print("reply:", result.get("reply"))


if __name__ == "__main__":
    main()
