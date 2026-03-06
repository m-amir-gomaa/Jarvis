# /THE_VAULT/jarvis/Makefile

.PHONY: setup test test-all status lint clean

VENV = /home/qwerty/NixOSenv/Jarvis/.venv
PY = $(VENV)/bin/python

setup:
	python -m venv $(VENV)
	$(VENV)/bin/pip install requests numpy watchdog aiohttp rank_bm25 filelock
	$(VENV)/bin/pip install 'mineru[pipeline]'

test-mvp1:
	$(PY) lib/ollama_client.py

test-mvp2:
	$(PY) tools/chunker.py test_data/sample.md --by-heading

test-mvp3:
	$(PY) tools/cleaner.py test_data/sample.md

test-mvp5:
	$(PY) pipelines/ingest.py --once test_data/sample.md

test-mvp7:
	$(PY) pipelines/agent_loop.py --task python_sum --user-prompt "sum a list" --output /tmp/out.py

test-all: test-mvp1 test-mvp2 test-mvp3 test-mvp5 test-mvp7
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
