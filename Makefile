# /THE_VAULT/jarvis/Makefile

.PHONY: setup test test-all status lint clean

JARVIS_ROOT ?= $(shell pwd)
export PYTHONPATH = $(JARVIS_ROOT)
REPO_DIR = $(JARVIS_ROOT)

VENV = $(JARVIS_ROOT)/.venv
PY = $(VENV)/bin/python

setup:
	python -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r requirements-v2.txt
	$(VENV)/bin/pip install 'mineru[pipeline]'

rust-build:
	@echo "Unloading Ollama models to free RAM before Rust build..."
	ollama stop qwen3:14b-q4_K_M || true
	ollama stop qwen3:8b || true
	cargo build --release --manifest-path jarvis-monitor/Cargo.toml
	cp jarvis-monitor/target/release/jarvis-monitor bin/jarvis-monitor
	@echo "Rust build complete. Restart Ollama if needed: ollama run qwen3:14b-q4_K_M"

.PHONY: rust-build

test-mvp1:
	$(PY) lib/ollama_client.py

test-mvp2:
	$(PY) tools/chunker.py test_data/sample.md --strategy heading

test-mvp3:
	$(PY) tools/cleaner.py test_data/chunks/chunks_manifest.json

test-mvp5:
	$(PY) pipelines/ingest.py --once test_data/sample.md

test-mvp7:
	$(PY) pipelines/agent_loop.py --task python_sum --user-prompt "sum a list" --output /tmp/out.py

test-budget:
	$(PY) tools/test_budget.py

test-budget-session:
	$(PY) tools/test_budget_session.py

test-router:
	$(PY) tools/test_router.py

test-cloud:
	$(PY) tools/test_cloud.py

test-llm:
	$(PY) tools/test_llm.py

test-memory:
	$(PY) tools/test_memory.py

test-tools:
	$(PY) tools/test_tools.py

test-react:
	$(PY) tools/test_react.py

migrate-vectors:
	$(PY) tools/migrate_vectors.py

test-semantic:
	$(PY) tools/test_semantic.py

test-phase-1:
	$(PY) -m pytest tests/security/ -v --tb=short
	@echo "Phase 1 gate: PASSED"

test-phase-2:
	$(PY) -m pytest tests/ers/ -v --tb=short
	@echo "Phase 2 gate: PASSED"

test-phase-3:
	$(PY) -m pytest tests/models/ -v --tb=short
	@echo "Phase 3 gate: PASSED"

test-phase-4:
	$(PY) -m pytest tests/ide/ -v --tb=short
	@echo "Phase 4 gate: PASSED"

test-all: test-phase-1 test-phase-2 test-phase-3 test-phase-4 test-mvp1 test-mvp2 test-mvp3 test-mvp5 test-mvp7 test-budget test-budget-session test-router test-cloud test-llm test-memory test-tools test-react test-semantic
	@echo "All tests passed"

status:
	@echo "Service Status:"
	@systemctl --user is-active jarvis-ingest || echo "ingest: stopped"
	@systemctl --user is-active jarvis-coding-agent || echo "coding-agent: stopped"
	@systemctl --user is-active jarvis-health-monitor || echo "health-monitor: stopped"
	@systemctl --user is-active jarvis-git-summarizer || echo "git-summarizer: stopped"

lint:
	$(PY) -m py_compile lib/ollama_client.py lib/event_bus.py lib/model_router.py
	@echo "Lint passed"

clean:
	find $(REPO_DIR)/logs/ -name "*.lock" -delete
	find $(REPO_DIR)/inbox/ -name "*.tmp" -delete

clean-logs:
	bash bin/clean_logs.sh
