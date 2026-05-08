# WineLedger — common tasks (GNU Make: Git Bash / WSL / macOS / Linux)
PY ?= python3
PIP ?= $(PY) -m pip
PORT ?= 8000

# On some systems (notably ROS installs), pytest auto-loads external plugins via
# entrypoints and can fail due to unrelated dependencies. Default to disabling
# auto-load for repeatable project tests. Override with:
#   make PYTEST_DISABLE_PLUGIN_AUTOLOAD=0 test
PYTEST_DISABLE_PLUGIN_AUTOLOAD ?= 1

.PHONY: help install install-backend install-frontend test dev-backend dev-frontend \
        cardano-status cardano-dryrun cardano-submissions

help:
	@echo WineLedger targets:
	@echo   make install           - pip install + npm install in frontend
	@echo   make install-backend   - pip install -r requirements.txt
	@echo   make install-frontend  - npm install in frontend/
	@echo   make test              - pytest
	@echo   make dev-backend       - uvicorn with reload on port $(PORT)
	@echo   make dev-frontend      - Vite dev server \(proxies to $(PORT)\)
	@echo   make cardano-status    - GET /cardano/status from the running backend
	@echo   make cardano-dryrun    - POST /cardano/dryrun to preview the next datum
	@echo   make cardano-submissions - GET /cardano/submissions
	@echo ""
	@echo Run backend and frontend in two terminals.

install: install-backend install-frontend

install-backend:
	$(PIP) install -r requirements.txt

install-frontend:
	cd frontend && npm install

test:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=$(PYTEST_DISABLE_PLUGIN_AUTOLOAD) $(PY) -m pytest

dev-backend:
	$(PY) -m uvicorn app.main:app --reload --host 127.0.0.1 --port $(PORT)

dev-frontend:
	cd frontend && npm run dev

cardano-status:
	curl -fsS http://127.0.0.1:$(PORT)/cardano/status

cardano-dryrun:
	curl -fsS -X POST http://127.0.0.1:$(PORT)/cardano/dryrun

cardano-submissions:
	curl -fsS http://127.0.0.1:$(PORT)/cardano/submissions
