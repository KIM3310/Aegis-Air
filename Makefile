PYTHON ?= python3
VENV ?= .venv
VENV_BIN := $(VENV)/bin
RUN_PYTHON := $(VENV_BIN)/python
RUN_UVICORN := $(VENV_BIN)/uvicorn

.PHONY: help setup run-target run-engine smoke test replay verify check

help:
	@printf '%s\n' \
	  'Aegis-Air local tasks' \
	  '  make setup       # create .venv and install dev dependencies' \
	  '  make run-target  # run demo target API on :8000' \
	  '  make run-engine  # run engine + frontend on :8001' \
	  '  make smoke       # quick regression surface checks' \
	  '  make test        # full pytest run' \
	  '  make replay      # print replay suite JSON' \
	  '  make verify      # compileall + pytest + replay suite'

setup:
	$(PYTHON) -m venv $(VENV)
	$(RUN_PYTHON) -m pip install --upgrade pip
	$(RUN_PYTHON) -m pip install -e ".[dev]"

run-target:
	$(RUN_UVICORN) app.main:app --port 8000

run-engine:
	$(RUN_UVICORN) aegis_engine.main:app --port 8001

smoke:
	$(RUN_PYTHON) -m pytest -q tests/test_frontend_contract.py tests/test_meta_endpoints.py tests/test_runtime_store.py

test:
	$(RUN_PYTHON) -m pytest -q

replay:
	$(RUN_PYTHON) scripts/run_replay_suite.py

verify:
	$(RUN_PYTHON) -m compileall -q .
	$(RUN_PYTHON) -m pytest -q
	$(RUN_PYTHON) scripts/run_replay_suite.py

check: verify
