from __future__ import annotations

import sys
from pathlib import Path

# `python scripts/...` from backend/ does not add backend to sys.path (unlike pytest/uvicorn).
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.agent.triage import classify_message_with_gemini


def main() -> None:
    result = classify_message_with_gemini("seene mein dard ho raha hai")
    print(result.model_dump())


if __name__ == "__main__":
    main()

