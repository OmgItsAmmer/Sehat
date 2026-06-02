.PHONY: dev dev-reload kill-port install-dev lint test test-unit test-integration test-system

# Default: no --reload so webhook prints show in the terminal on Windows.
dev:
	cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info

# Hot reload (on Windows, stdout from the worker may not appear in this terminal).
dev-reload:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level info

# Free port 8000 when a previous uvicorn was left running (common on Windows).
kill-port:
	powershell -Command "$$p = (Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue).OwningProcess | Select-Object -Unique; if ($$p) { $$p | ForEach-Object { Stop-Process -Id $$_ -Force }; Write-Host 'Killed PID(s) on port 8000:' $$p } else { Write-Host 'Port 8000 is free' }"

install-dev:
	cd backend && pip install -r requirements-dev.txt

lint:
	cd backend && ruff check app tests && ruff format --check app tests && mypy app

test: test-unit test-integration test-system

test-unit:
	cd backend && pytest tests/unit -m unit -v

test-integration:
	cd backend && pytest tests/integration -m integration -v

test-system:
	cd backend && pytest tests/system -m system -v

migrate:
	cd backend && alembic upgrade head

triage-scratch:
	cd backend && python scripts/scratch_gemini_triage.py

graph-scratch:
	cd backend && python scripts/scratch_langgraph_triage.py
