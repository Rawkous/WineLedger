# WineLedger — common tasks (GNU Make: Git Bash / WSL / macOS / Linux)
PY ?= python
PIP ?= $(PY) -m pip

.PHONY: help install install-backend install-frontend test dev-backend dev-frontend

help:
	@echo WineLedger targets:
	@echo   make install           - pip install + npm install in frontend
	@echo   make install-backend   - pip install -r requirements.txt
	@echo   make install-frontend  - npm install in frontend/
	@echo   make test              - pytest
	@echo   make dev-backend       - uvicorn with reload on port 8000
	@echo   make dev-frontend      - Vite dev server \(proxies to 8000\)
	@echo ""
	@echo Run backend and frontend in two terminals.

install: install-backend install-frontend

install-backend:
	$(PIP) install -r requirements.txt

install-frontend:
	cd frontend && npm install

test:
	$(PY) -m pytest

dev-backend:
	$(PY) -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

dev-frontend:
	cd frontend && npm run dev
