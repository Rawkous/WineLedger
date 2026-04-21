# WineLedger — common tasks (GNU Make: Git Bash / WSL / macOS / Linux)
PY ?= python3
PIP ?= $(PY) -m pip
PORT ?= 8000

# On some systems (notably ROS installs), pytest auto-loads external plugins via
# entrypoints and can fail due to unrelated dependencies. Default to disabling
# auto-load for repeatable project tests. Override with:
#   make PYTEST_DISABLE_PLUGIN_AUTOLOAD=0 test
PYTEST_DISABLE_PLUGIN_AUTOLOAD ?= 1

.PHONY: help install install-backend install-frontend test dev-backend dev-frontend

help:
	@echo WineLedger targets:
	@echo   make install           - pip install + npm install in frontend
	@echo   make install-backend   - pip install -r requirements.txt
	@echo   make install-frontend  - npm install in frontend/
	@echo   make test              - pytest
	@echo   make dev-backend       - uvicorn with reload on port $(PORT)
	@echo   make dev-frontend      - Vite dev server \(proxies to $(PORT)\)
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
