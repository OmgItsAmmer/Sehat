# Alembic Migrations Runbook (Sehat)

This runbook explains how database schema changes are managed with **Alembic** in this repo, and the exact commands to create/apply migrations against **Neon Postgres**.

---

## Where Alembic lives in this repo

- **Config**: `backend/alembic.ini`
- **Migration env**: `backend/database/migrations/env.py`
- **Migration files**: `backend/database/migrations/versions/*.py`
- **SQLAlchemy models**: `backend/app/models/*`
- **DB URL source**: `backend/app/config.py` → reads `DATABASE_URL` from your `.env`

Key detail: migrations require **`DATABASE_URL`** (Neon connection string). If it’s missing, Alembic will error by design.

---

## Prerequisites (one-time)

### 1) Install backend dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2) Configure `DATABASE_URL`

In repo root `.env`, set:

```env
DATABASE_URL=postgresql+psycopg://<user>:<password>@<host>/<db>?sslmode=require
```

Notes:
- Neon typically requires TLS; `sslmode=require` is common.
- Either `postgresql://...` or `postgresql+psycopg://...` works with SQLAlchemy 2 + psycopg.

---

## The two commands you’ll use most

### Apply all migrations (bring DB up to date)

From repo root:

```bash
make migrate
```

This runs:
- `alembic upgrade head`

### Check current revision (what your DB is on)

```bash
cd backend
alembic current
```

---

## Typical workflow: “I changed models, now I need a migration”

### Step 1) Update or add SQLAlchemy models

Examples:
- Add a column to `backend/app/models/patient.py`
- Add a new table in `backend/app/models/*`

### Step 2) Create a new revision file

From `backend/`:

```bash
alembic revision -m "add <thing>"
```

This creates a new file in:
- `backend/database/migrations/versions/`

### Step 3) Edit the revision file (write upgrade/downgrade)

Open the generated file and implement:
- `upgrade()`: forward schema change
- `downgrade()`: rollback

### Step 4) Apply it to Neon

```bash
make migrate
```

---

## Recommended patterns (safe + predictable)

- **Prefer explicit migrations**: write `op.add_column`, `op.create_table`, etc. rather than relying on autogenerate.
- **Always include downgrade**: assume you might need to rollback in demo/prod.
- **Keep migrations small**: one logical change per revision.

---

## Common Alembic commands (cheat sheet)

Run these from `backend/` unless noted.

### Upgrade / downgrade

```bash
alembic upgrade head
alembic downgrade -1
```

### Inspect history

```bash
alembic history --verbose
alembic current
```

### Create an empty revision

```bash
alembic revision -m "describe change"
```

---

## How Sehat wires metadata (important)

Alembic needs to know what tables exist in SQLAlchemy metadata. This repo does that in:

- `backend/database/migrations/env.py`
  - imports `app.models.patient` and `app.models.message`
  - sets `target_metadata = Base.metadata` (from `backend/app/database/base.py`)

If you add a **new model file**, ensure it is imported somewhere that Alembic sees it (one of these patterns):

- Add it to `backend/app/models/__init__.py`, and import it in `env.py`, or
- Import the model module directly in `env.py`

Otherwise Alembic won’t “see” the table when you write migrations or run metadata-dependent tooling.

---

## Troubleshooting

### “DATABASE_URL is required to run migrations”

- Fix: set `DATABASE_URL` in `.env` (repo root) or in your shell environment.

### “alembic is not recognized” (Windows)

- Cause: Alembic CLI isn’t in PATH (deps not installed into your current venv).
- Fix:

```bash
cd backend
pip install -r requirements.txt
python -m alembic --help
```

If `python -m alembic` works, you can use that form instead of `alembic`.

### SSL / connection failures to Neon

- Ensure your Neon connection string includes SSL, often:
  - `?sslmode=require`
- Ensure IP allowlist / project settings in Neon permit your connection.

---

## What’s already in place

- Initial migration exists: `backend/database/migrations/versions/0001_init_patients_messages.py`
- Tables created:
  - `patients`
  - `messages`

