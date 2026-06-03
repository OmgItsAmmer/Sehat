# Fly.io + Vercel deployment runbook (Sehat)

**Goal (phase 10):** Public HTTPS URLs for the FastAPI backend and React dashboard, at the lowest practical cost.

```
WhatsApp → Green API → https://<api>.fly.dev/api/whatsapp/webhook → LangGraph → Neon + Upstash
Receptionist → https://<app>.vercel.app → VITE_API_URL → Fly API
```

**Code:** `backend/Dockerfile` · `backend/app/main.py` · `frontend/` (Vercel)  
**Time:** ~45 min first backend deploy · ~15 min first Vercel deploy · ~5 min per redeploy

---

## Cost strategy

Do **not** provision Postgres or Redis on Fly.io. Use external free tiers. Fly runs **only** the API container.

| Component | Where | Why |
|-----------|-------|-----|
| FastAPI API | Fly.io | One `shared-cpu-1x` VM, 256MB RAM |
| PostgreSQL | [Neon](https://neon.tech) | Already used in Phase 2; free tier |
| Redis | [Upstash](https://upstash.com) | Free serverless Redis; session memory from Phase 6 |
| Frontend (dashboard) | [Vercel](https://vercel.com) | Free hobby tier; static Vite build, global CDN |

**Fly cost knobs** (set in `fly.toml`):

- `min_machines_running = 0` — no always-on charge when idle
- `auto_stop_machines = "stop"` — machine stops after traffic drops
- `auto_start_machines = true` — wakes on incoming webhook
- `memory = "256mb"`, `cpu_kind = "shared"`, `cpus = 1` — smallest VM size

Fly’s free allowance typically covers **three** shared-cpu-1x 256MB machines. This setup uses **one** (API only). Vercel hobby tier covers the dashboard at **$0** for demos.

**Trade-off:** After idle, the first WhatsApp webhook may take **5–15 seconds** while the Fly machine cold-starts. Send a test message or `curl /health` a minute before your demo.

---

## Prerequisites

| Item | Notes |
|------|--------|
| [Fly.io account](https://fly.io/app/sign-up) | Credit card may be required; stay within free allowance |
| [Fly CLI](https://fly.io/docs/hands-on/install-flyctl/) | `fly version` |
| Neon `DATABASE_URL` | Same string as local `.env` — see [`alembic_migration_rubooks.md`](alembic_migration_rubooks.md) |
| Upstash Redis | Create a database → copy `rediss://...` URL |
| [Vercel account](https://vercel.com/signup) | Hobby tier — dashboard deploy |
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
fly launch --no-deploy --copy-config --region sin --no-db --no-redis -y
```

**Region:** Singapore = Fly code **`sin`** (not the word `singapore`). Confirm with `fly platform regions`.

If you prefer prompts instead of `-y`, still enter **`sin`** when asked for region.

- **App name:** e.g. `sehat-api` (globally unique → `sehat-api-<yourname>` if taken)
- **Postgres / Redis:** **No** — use Neon + Upstash
- **Deploy now:** **No** (`--no-deploy`)

This creates `backend/fly.toml`. Replace or merge with the cost-optimized template below.

### Recommended `backend/fly.toml`

```toml
app = "sehat-api"          # your chosen name (globally unique)
primary_region = "sin"     # Singapore — must be Fly code, not "singapore"

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

  [[http_service.checks]]
    grace_period = "20s"
    interval = "30s"
    method = "GET"
    path = "/health"
    timeout = "5s"

[[vm]]
  size = "shared-cpu-1x"
  memory = "256mb"
```

> **Note:** Fly occasionally changes `fly.toml` schema. If `fly deploy` warns about deprecated keys, run `fly config save` after `fly launch` and re-apply the `http_service` / `vm` settings above.

---

## 4. Set secrets (production env)

Never commit secrets. **On Windows, do not paste bash `fly secrets set \` blocks** — PowerShell treats `\` differently and breaks on `&` in URLs.

1. Put production values in repo-root **`.env`** (`DATABASE_URL`, `REDIS_URL` = Upstash `rediss://...`, `OPENAI_API_KEY`, `GREEN_API_*`, optional `SLACK_WEBHOOK_URL`). Do **not** paste shell commands into `.env`.
2. Run the project script (reads `.env`, calls `fly secrets import`):

```powershell
# From repo root (Windows 11)
powershell -ExecutionPolicy Bypass -File backend\scripts\Set-FlySecrets.ps1
```

```powershell
fly secrets list
```

Optional: different app name — `Set-FlySecrets.ps1 -App sehat-api-yourname`

**Manual one-liner** (only if you skip the script; single quotes required for Neon `&`):

```powershell
cd backend
fly secrets set DATABASE_URL='postgresql://USER:PASS@HOST/neondb?sslmode=require&channel_binding=require' REDIS_URL='rediss://default:TOKEN@HOST:6379' OPENAI_API_KEY='sk-...' GREEN_API_INSTANCE='...' GREEN_API_TOKEN='...'
```

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

## 7. Deploy frontend on Vercel

The receptionist dashboard lives in `frontend/`. Deploy it on **Vercel** (not Fly) so the API stays on a single cheap Fly machine.

**Deploy the Fly API first** (sections 3–5). You need the live API URL for `VITE_API_URL`.

### 7.1 SPA routing (`vercel.json`)

React Router uses client-side routes (`/cases/:phone`, `/analytics`, …). The repo includes `frontend/vercel.json` so deep links work on refresh:

```json
{ "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }] }
```
### 7.2 Connect repo to Vercel

1. Sign in at [vercel.com](https://vercel.com) → **Add New Project** → import this GitHub repo.
2. **Root Directory:** `frontend` (Edit → set to `frontend`).
3. **Framework Preset:** Vite (auto-detected).
4. **Build Command:** `npm run build` (default).
5. **Output Directory:** `dist` (default for Vite).

### 7.3 Environment variables (Vercel dashboard)

Project → **Settings → Environment Variables**:

| Name | Value | Environments |
|------|-------|--------------|
| `VITE_API_URL` | `https://<your-app>.fly.dev` | Production (and Preview if you want staging) |

No trailing slash. This is baked in at **build time** — change it in Vercel and redeploy if the Fly app URL changes.

Local dev stays unchanged: leave `VITE_API_URL` empty in `.env.development` and use the Vite proxy.

### 7.4 Deploy

Click **Deploy**, or push to the connected branch. Vercel assigns a URL like:

```
https://sehat-<team>.vercel.app
```

Optional: **Settings → Domains** for a custom domain.

### 7.5 Verify dashboard → API

1. Open the Vercel URL in a browser.
2. DevTools → Network: requests should go to `https://<your-app>.fly.dev/api/...`.
3. Confirm cases load and override buttons work.

The FastAPI app already allows cross-origin requests (`CORS allow_origins=["*"]`), so the Vercel origin can call the Fly API when `VITE_API_URL` is set.

### 7.6 Redeploy frontend

- **Automatic:** push to the branch Vercel watches (usually `main`).
- **Manual:** Vercel dashboard → **Deployments → Redeploy**.
- **CLI:** `npm i -g vercel && cd frontend && vercel --prod`

After changing `VITE_API_URL`, trigger a new production deploy so the build picks up the value.

---

## 8. Redeploy after code changes

**Backend:**

```bash
cd backend
fly deploy
```

**Frontend:** push to Git (Vercel auto-builds) or `vercel --prod` from `frontend/`.

If you changed the DB schema:

```bash
make migrate    # against Neon, from laptop
fly deploy      # only if application code changed
```

---

## 9. Pre-demo checklist

```
[ ] fly status shows API healthy (or will start on request)
[ ] curl https://<api>.fly.dev/health → ok
[ ] fly secrets list includes DATABASE_URL, REDIS_URL, GEMINI_*, GREEN_API_*, SLACK_*
[ ] make migrate applied on Neon (alembic current = head)
[ ] Green API webhook URL = https://<api>.fly.dev/api/whatsapp/webhook
[ ] Test WhatsApp message received (fly logs)
[ ] Slack P1 test alert received
[ ] Vercel production URL opens dashboard
[ ] VITE_API_URL on Vercel points at Fly API (redeploy if you changed it)
[ ] Dashboard loads cases from live API (Network tab)
[ ] Cold-start ping sent ~1 min before live demo (Fly API)
[ ] Three scripted scenarios (plan.md Phase 10) pass on live URLs
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
| Dashboard empty / API errors | Wrong or missing `VITE_API_URL` | Set on Vercel → redeploy frontend |
| Vercel 404 on refresh | No SPA rewrite | Add `frontend/vercel.json` (section 7.1) |
| CORS blocked | Rare — API allows `*` | Ensure `VITE_API_URL` is full Fly URL, not relative |

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

**Backend (Fly.io)** — GitHub Actions with `FLY_API_TOKEN`:

```yaml
- uses: superfly/flyctl-actions/setup-flyctl@master
- run: fly deploy --remote-only
  working-directory: backend
  env:
    FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

Create token: `fly tokens create deploy -x 999999h`. Store as repo secret `FLY_API_TOKEN`.

**Frontend (Vercel)** — connect the repo in the Vercel dashboard (section 7). Vercel builds on push automatically; no extra workflow required unless you use [Vercel GitHub integration](https://vercel.com/docs/deployments/git) with preview deployments.

---

## Quick reference

| Task | Command / location |
|------|-------------------|
| Deploy API | `cd backend && fly deploy` |
| Deploy dashboard | Vercel dashboard or `cd frontend && vercel --prod` |
| API logs | `fly logs` |
| API secrets | `fly secrets set KEY=value` |
| API health | `curl https://<api>.fly.dev/health` |
| Frontend env | Vercel → Settings → Environment Variables → `VITE_API_URL` |
| Migrations | `make migrate` (Neon, local) |
| Fly dashboard | `fly dashboard` |
