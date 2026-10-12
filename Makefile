.PHONY: migrate test import-initial import tick worker api demos smoke verify-clean
migrate:
	PYTHONPATH=backend .venv/bin/python -m retrovault.cli migrate
test:
	PYTHONPATH=backend .venv/bin/pytest backend/tests -q
import-initial:
	PYTHONPATH=backend .venv/bin/python -m retrovault.cli import --initial
import:
	PYTHONPATH=backend .venv/bin/python -m retrovault.cli import
tick:
	PYTHONPATH=backend .venv/bin/python -m retrovault.cli tick
worker:
	PYTHONPATH=backend .venv/bin/python -m retrovault.cli worker
api:
	PYTHONPATH=backend .venv/bin/uvicorn retrovault.main:app --host 127.0.0.1 --port 8000
demos:
	PYTHONPATH=backend .venv/bin/python -m retrovault.cli demos
smoke:
	.venv/bin/python backend/scripts/smoke.py
verify-clean:
	PYTHONPATH=backend .venv/bin/python backend/scripts/verify_clean.py
