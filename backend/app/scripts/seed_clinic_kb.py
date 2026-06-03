"""Seed clinic knowledge chunks: python -m app.scripts.seed_clinic_kb"""

from __future__ import annotations

import sys

from app.database.session import db_is_available, get_sessionmaker
from app.services.rag import seed_kb


def main() -> int:
    if not db_is_available():
        print("DATABASE_URL not configured or Postgres unavailable.", file=sys.stderr)
        return 1
    SessionLocal = get_sessionmaker()
    with SessionLocal() as db:
        n = seed_kb(db)
    print(f"Seeded {n} clinic knowledge chunks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
