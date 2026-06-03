# Phase 7 — Receptionist dashboard + human override

**Status:** Implemented.

## Flow

1. Low-confidence classify (`confidence < 0.75`) → `await_human_review` node → graph ends with `awaiting_human_review=True`.
2. Clinic dashboard lists cases from Redis session memory (`GET /api/cases`).
3. Sana clicks **Agree / Upgrade / Downgrade** → `POST /api/cases/{phone}/override`.
4. `override.apply_override` logs to Postgres `overrides`, resumes graph, saves session, sends WhatsApp reply.

## Files

| File | Role |
|------|------|
| `backend/app/services/pipeline.py` | Inbound + override resume orchestration |
| `backend/app/services/override.py` | Audit log + resume |
| `backend/app/api/human_override.py` | REST endpoint |
| `backend/app/models/override.py` | Alembic `0002_overrides` |
| `frontend/src/components/dashboard/OverrideButtons.tsx` | UI |

Run migration: `make migrate`
