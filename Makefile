.PHONY: dev dev-reload kill-port install-dev lint test test-unit test-integration test-phases test-system eval frontend-dev frontend-install fly-secrets

# Default: no --reload so webhook prints show in the terminal on Windows.
dev:
	cd backend && venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info

# Hot reload (on Windows, stdout from the worker may not appear in this terminal).
dev-reload:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level info

# Free port 8000 when a previous uvicorn was left running (common on Windows).
kill-port:
	powershell -Command "$$p = (Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue).OwningProcess | Select-Object -Unique; if ($$p) { $$p | ForEach-Object { Stop-Process -Id $$_ -Force }; Write-Host 'Killed PID(s) on port 8000:' $$p } else { Write-Host 'Port 8000 is free' }"

install-dev:
	cd backend && pip install -r requirements-dev.txt

# Windows: push repo-root .env to Fly (see backend/scripts/Set-FlySecrets.ps1)
fly-secrets:
	powershell -ExecutionPolicy Bypass -File backend/scripts/Set-FlySecrets.ps1

lint:
	cd backend && ruff check app tests && ruff format --check app tests && mypy app

test: test-unit test-integration test-system

test-unit:
	cd backend && pytest tests/unit tests/phases -m unit -v

test-integration:
	cd backend && pytest tests/integration tests/phases -m integration -v

test-phases:
	cd backend && pytest tests/phases -v

test-system:
	cd backend && pytest tests/system -m system -v

migrate:
	cd backend && alembic upgrade head

# Wipe Redis/in-memory triage sessions (dashboard queue). Does not touch Postgres.
clear-sessions:
	curl -s -X POST http://127.0.0.1:8000/api/dev/clear-sessions

triage-scratch:
	cd backend && python scripts/scratch_openai_triage.py

graph-scratch:
	cd backend && python scripts/scratch_langgraph_triage.py

eval:
	cd backend && python -m evals.test_classification --show-errors

frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

# Run API + dashboard together (two terminals worth of work in one make target on Windows).
dev-all:
	@echo Start backend in one terminal: make dev
	@echo Start frontend in another: make frontend-dev
	@echo Frontend uses http://127.0.0.1:8000 — see frontend/.env.development
