# Fly.io deployment runbook (Sehat)

**Goal (phase 10):** Public HTTPS URL for the FastAPI backend (and optionally the React dashboard), at the lowest practical cost.

```
WhatsApp → Green API → https://<app>.fly.dev/api/whatsapp/webhook → LangGraph → Neon + Upstash
```

**Code:** `backend/Dockerfile` · `backend/app/main.py`  
**Time:** ~45 minutes first deploy · ~5 minutes per redeploy

---

## Cost strategy

Do **not** provision Postgres or Redis on Fly.io for this project. Use external free tiers and run only the API container on Fly.

| Component | Where | Why |
|-----------|-------|-----|
| FastAPI API | Fly.io | One `shared-cpu-1x` VM, 256MB RAM |
| PostgreSQL | [Neon](https://neon.tech) | Already used in Phase 2; free tier, no Fly Postgres bill |
| Redis | [Upstash](https://upstash.com) | Free serverless Redis; session memory from Phase 6 |
| Frontend | Fly static app *or* local `npm run dev` | Optional second free Fly machine |

**Fly cost knobs** (set in `fly.toml`):

- `min_machines_running = 0` — no always-on charge when idle
- `auto_stop_machines = "stop"` — machine stops after traffic drops
- `auto_start_machines = true` — wakes on incoming webhook
- `memory = "256mb"`, `cpu_kind = "shared"`, `cpus = 1` — smallest VM size

Fly’s free allowance typically covers **three** shared-cpu-1x 256MB machines. This setup uses one for the API (and optionally one for the dashboard).

**Trade-off:** After idle, the first WhatsApp webhook may take **5–15 seconds** while the machine cold-starts. Send a test message or `curl /health` a minute before your demo.

---

## Prerequisites

| Item | Notes |
|------|--------|
| [Fly.io account](https://fly.io/app/sign-up) | Credit card may be required; stay within free allowance |
| [Fly CLI](https://fly.io/docs/hands-on/install-flyctl/) | `fly version` |
| Neon `DATABASE_URL` | Same string as local `.env` — see [`alembic_migration_rubooks.md`](alembic_migration_rubooks.md) |
| Upstash Redis | Create a database → copy `rediss://...` URL |
| Green API instance | Authorized and online |
| `.env` values | `GEMINI_API_KEY`, `GREEN_API_*`, `SLACK_WEBHOOK_URL`, etc. |

---

## 1. Upstash Redis (free)

1. Sign up at [upstash.com](https://upstash.com) → **Create database**.
2. Region: pick one close to your Fly region (e.g. `ap-southeast-1` if Fly app is `sin`).
3. Copy the **Redis URL** (TLS form: `rediss://default:...@....upstash.io:6379`).
4. You will set this as `REDIS_URL` on Fly (step 4).

Local dev can keep using Docker Redis; production uses Upstash only.

---

## 2. Run migrations on Neon

Migrations run **from your laptop** against Neon — not inside the Fly container (the Dockerfile only copies `app/`, not Alembic).

From repo root, with `DATABASE_URL` in `.env`:

```bash
make migrate
```

Verify:

```bash
cd backend && alembic current
# should show latest revision (e.g. 0002_overrides)
```

---

## 3. Create the Fly app (backend)

From repo root:

```bash
fly auth login
cd backend
fly launch --no-deploy
```

When prompted:

- **App name:** e.g. `sehat-api` (must be globally unique → `sehat-api-<yourname>`)
- **Region:** nearest to users/demo (e.g. `sin` Singapore, `bom` Mumbai)
- **Postgres / Redis:** **No** — use Neon + Upstash
- **Deploy now:** **No**

This creates `backend/fly.toml`. Replace or merge with the cost-optimized template below.

### Recommended `backend/fly.toml`

```toml
app = "sehat-api"          # your chosen name
primary_region = "sin"     # your chosen region

[build]
  dockerfile = "Dockerfile"

[env]
  PORT = "8000"

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = "stop"
  auto_start_machines = true
  min_machines_running = 0
  processes = ["app"]

[[vm]]
  size = "shared-cpu-1x"
  memory = "256mb"

[checks]
  [checks.health]
    grace_period = "20s"
    interval = "30s"
    method = "GET"
    path = "/health"
    timeout = "5s"
```

> **Note:** Fly occasionally changes `fly.toml` schema. If `fly deploy` warns about deprecated keys, run `fly config save` after `fly launch` and re-apply the `http_service` / `vm` settings above.

---

## 4. Set secrets (production env)

Never commit secrets. Set them on Fly:

```bash
cd backend

fly secrets set \
  DATABASE_URL="postgresql+psycopg://..." \
  REDIS_URL="rediss://default:...@....upstash.io:6379" \
  GEMINI_API_KEY="..." \
  GEMINI_MODEL="gemini-3-flash-preview" \
  GREEN_API_INSTANCE="..." \
  GREEN_API_TOKEN="..." \
  SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
```

Optional keys (if used): `CLERK_SECRET_KEY`, `OPENAI_API_KEY`.

List without values:

```bash
fly secrets list
```

---

## 5. Deploy the API

```bash
cd backend
fly deploy
```

When finished:

```bash
fly status
fly logs
curl https://<your-app>.fly.dev/health
# {"status":"ok"}
```

Your public base URL: `https://<your-app>.fly.dev`

---

## 6. Point Green API at Fly

1. Open [Green API console](https://console.green-api.com) → your instance.
2. Set **Webhook URL** to:

   ```
   https://<your-app>.fly.dev/api/whatsapp/webhook
   ```

3. Save. Send a WhatsApp message to the linked number.
4. Watch logs: `fly logs` — you should see the webhook hit (may delay on cold start).

Details: [`Green-api-whatsapp-integration_runbook.md`](Green-api-whatsapp-integration_runbook.md).

---

## 7. Frontend (optional, still cheap)

The dashboard is a separate Vite app. Two options:

### A — Local dashboard, live API (cheapest)

In `frontend/.env`:

```env
VITE_API_BASE_URL=https://<your-app>.fly.dev
```

```bash
make frontend-dev
```

Open the local Vite URL; it calls the Fly API. **Zero extra Fly machines.**

### B — Static dashboard on Fly (second free VM)

1. Build with the live API URL:

   ```bash
   cd frontend
   echo "VITE_API_BASE_URL=https://<your-app>.fly.dev" > .env.production
   npm run build
   ```

2. From `frontend/`, create a minimal static Fly app (one-time):

   ```bash
   fly launch --no-deploy --name sehat-dashboard
   ```

3. Use a static `Dockerfile` (nginx serving `dist/`) or Fly’s [static asset pattern](https://fly.io/docs/languages-and-frameworks/static/). Set the same `auto_stop_machines` / `min_machines_running = 0` in `fly.toml`.

4. `fly deploy` from `frontend/`.

For a hackathon demo, **option A is enough**.

---

## 8. Redeploy after code changes

```bash
cd backend
fly deploy
```

If you changed the DB schema:

```bash
make migrate    # against Neon, from laptop
fly deploy      # only if application code changed
```

---

## 9. Pre-demo checklist

```
[ ] fly status shows app healthy (or will start on request)
[ ] curl https://<app>.fly.dev/health → ok
[ ] fly secrets list includes DATABASE_URL, REDIS_URL, GEMINI_*, GREEN_API_*, SLACK_*
[ ] make migrate applied on Neon (alembic current = head)
[ ] Green API webhook URL = https://<app>.fly.dev/api/whatsapp/webhook
[ ] Test WhatsApp message received (fly logs)
[ ] Slack P1 test alert received
[ ] Cold-start ping sent ~1 min before live demo
[ ] Three scripted scenarios (plan.md Phase 10) pass on live URL
[ ] Screen recording backup recorded
```

---

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Webhook timeout from Green API | Machine stopped (cold start) | Retry; or set `min_machines_running = 1` only during demo window |
| `502` / app not listening | Wrong `internal_port` | Must be `8000`; Dockerfile uses `PORT` env |
| DB connection errors | Wrong `DATABASE_URL` or Neon IP allow | Neon: allow all IPs or Fly egress; use `sslmode=require` |
| Redis errors | Upstash URL or TLS | Use `rediss://` URL from Upstash console |
| Migrations missing tables | Never ran `make migrate` | Run against Neon from laptop |
| Secrets not picked up | Set after deploy | `fly secrets set ...` triggers redeploy automatically |

**Logs and SSH:**

```bash
fly logs
fly ssh console -C "printenv | grep -E 'DATABASE|REDIS|GEMINI'"   # names only — values are hidden
```

**Scale up temporarily for demo** (accepts small hourly cost):

```bash
fly scale count 1 --yes
# or in fly.toml: min_machines_running = 1
fly deploy
```

**Tear down** (stop billing beyond free tier):

```bash
fly apps destroy sehat-api
```

---

## 11. CI/CD (optional)

GitHub Actions can deploy with `FLY_API_TOKEN`:

```yaml
- uses: superfly/flyctl-actions/setup-flyctl@master
- run: fly deploy --remote-only
  working-directory: backend
  env:
    FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

Create token: `fly tokens create deploy -x 999999h`. Store as repo secret `FLY_API_TOKEN`.

This replaces any Railway-based workflow when you switch CD over.

---

## Quick reference

| Task | Command |
|------|---------|
| Deploy API | `cd backend && fly deploy` |
| Logs | `fly logs` |
| Secrets | `fly secrets set KEY=value` |
| Health | `curl https://<app>.fly.dev/health` |
| Migrations | `make migrate` (Neon, local) |
| Open dashboard | `fly dashboard` |
