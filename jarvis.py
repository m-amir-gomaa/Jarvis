#!/usr/bin/env python3
"""
MVP BIG — Jarvis Unified CLI
/home/qwerty/NixOSenv/Jarvis/jarvis.py  (extended with full routing)

Natural language front-end to all Jarvis pipelines.
Uses Mistral-7B intent classification to route commands.

Usage:
  jarvis 'clean this pdf for notebooklm'
  jarvis status
  jarvis start
  jarvis stop
  jarvis pause / resume
  jarvis thumbs-up / thumbs-down
  jarvis help
  jarvis --version

CRITICAL: service lifecycle via systemctl --user (NOT subprocess.Popen)
"""

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(os.environ.get("JARVIS_ROOT", Path(__file__).resolve().parent))
sys.path.insert(0, str(BASE_DIR))
from lib.event_bus import emit
import secrets as _secrets

REPO_DIR = BASE_DIR
HISTORY_PATH = BASE_DIR / "logs" / "history.jsonl"
FEEDBACK_PATH = BASE_DIR / "logs" / "feedback.jsonl"
VERSION = "0.1.0"
VENV_PY = str(BASE_DIR / ".venv" / "bin" / "python")
_VAULT_ROOT = Path(os.environ.get("VAULT_ROOT", "/THE_VAULT/jarvis"))

# ── CLI V2 Security Context (Phase A) ─────────────────────────────────────────
# Creates an ADMIN-trust SecurityContext for CLI-triggered operations.
# shadow_mode stays ON until Phase E (all pipelines migrated + tested).
# This is a best-effort init: if security libs fail to import (e.g. venv not
# activated), CLI still works — it just has no audit trail.
_CLI_CTX = None

def _create_cli_ctx():
    """Lazy-init CLI SecurityContext with ADMIN trust. Called once at dispatch time."""
    global _CLI_CTX
    if _CLI_CTX is not None:
        return _CLI_CTX
    try:
        from lib.security.context import SecurityContext
        from lib.security.audit import AuditLogger
        from lib.security.store import GrantStore

        audit = AuditLogger(_VAULT_ROOT / "databases" / "security_audit.db")
        ctx = SecurityContext(agent_id="cli", trust_level=3)  # ADMIN
        store = GrantStore(audit)
        restored = store.load_persistent_grants(ctx)
        if restored > 0:
            print(f"[Jarvis] Restored {restored} persistent capability grant(s).")
        _CLI_CTX = ctx
    except Exception as e:
        # Graceful degradation — CLI still works without security engine
        print(f"[Jarvis] Security context unavailable: {e}", file=sys.stderr)
    return _CLI_CTX


def _shadow_require(capability: str, reason: str = "") -> None:
    """
    Log a capability requirement to the audit trail (shadow mode — no enforcement).
    Call this wherever the CLI would need a capability check if fully migrated.
    """
    ctx = _create_cli_ctx()
    if ctx is None:
        return
    try:
        from lib.security.context import shadow_require
        shadow_require(ctx, capability)
    except Exception:
        pass


def run_pipeline(cmd: list, timeout: int = 300, risk_level: str = "low"):
    if risk_level == "high":
        print(f"⚠️  HIGH RISK OPERATION DETECTED: {' '.join(cmd)}")
        confirm = input("This operation may significantly alter your system. Proceed? [y/N] ").strip().lower()
        if confirm not in ("y", "yes"):
            print("Operation aborted by user.")
            return False
            
    env = {**os.environ, "PYTHONPATH": str(BASE_DIR)}
    result = subprocess.run(cmd, env=env, timeout=timeout)
    return result.returncode == 0

SERVICES = [
    "jarvis-health-monitor",
    "jarvis-git-monitor",
    "jarvis-coding-agent",
    "jarvis-self-healer",
]

INTENT_PROMPT = """You are an intent classifier for a command-line AI assistant.
Classify the user input into exactly ONE of these intents and respond with valid JSON only.

Intents:
- [ ] generate_nix: write or fix a NixOS module or config
- [ ] optimize_prompt: improve a prompt for a task
- [ ] validate_nixos: check NixOS configuration for errors
- [ ] git_summary: summarize recent git commits
- [ ] knowledge_graph_query: specifically for "what do I know about <topic>" or "show me the graph for <topic>". Use this for synthesizing overall knowledge or "what do I know" style questions.
- [ ] query_knowledge: ask a SPECIFIC QUESTION about technical facts or how things work.
- [ ] plan: decompose a high-level goal into a sequence of steps or a strategic plan. Use this for complex goals like "setup a new project" or "fix a series of issues".
- [ ] manage_calendar: add or list calendar events. Keywords: "schedule", "meeting", "event", "calendar", "tomorrow".
- [ ] manage_tasks: add, list, or complete tasks. Keywords: "todo", "task", "remember to", "done", "complete task".
- [ ] refactor: perform complex code changes across multiple files. Keywords: "refactor", "extract", "move", "rename class", "restructure".
- [ ] explain_error: provide diagnostic lens on a compiler or runtime error. Keywords: "explain error", "why did it fail", "fix this error".
- [ ] manage_models: list local and cloud models. Keywords: "models", "show models", "what models".
- [ ] manage_keys: list API keys and environment variables. Keywords: "keys", "api keys", "environment".
- [ ] toggle_voice: enable or disable voice gateway. Keywords: "toggle voice", "mute microphone", "voice commands on/off".

Response format (JSON only, no other text):
{"intent": "<intent>", "args": {"file": "<file if mentioned>", "query": "<query if applicable>"}}

User input: """


# ── Intent Classification ─────────────────────────────────────────────────────

def classify_intent(user_input: str) -> dict:
    try:
        from lib.ollama_client import is_healthy
        from lib.llm import ask, Privacy

        if not is_healthy():
            return {"intent": "unknown", "args": {}}

        # ask() takes a positional prompt string — no messages= kwarg
        response = ask(INTENT_PROMPT + user_input, task="classify", privacy=Privacy.INTERNAL, thinking=False)

        # ask() returns LLMResponse object — extract text
        text = response.content if hasattr(response, "content") else str(response)

        # Extract JSON from response
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception as e:
        print(f"[Jarvis] Intent classification failed: {e}", file=sys.stderr)

    return {"intent": "unknown", "args": {}}


# ── Service Management ────────────────────────────────────────────────────────

def systemctl_user(action: str, service: str) -> bool:
    result = subprocess.run(
        ["systemctl", "--user", action, f"{service}.service"],
        capture_output=True, text=True, timeout=10
    )
    return result.returncode == 0


def cmd_start():
    print("[Jarvis] Starting all services...")
    for svc in SERVICES:
        ok = systemctl_user("start", svc)
        print(f"  {svc}: {'✓' if ok else '✗ (failed or not installed)'}")


def cmd_stop():
    print("[Jarvis] Stopping all services...")
    for svc in SERVICES:
        ok = systemctl_user("stop", svc)
        print(f"  {svc}: {'✓ stopped' if ok else '✗'}")


def cmd_status(short=False):
    if not short:
        print("[Jarvis] Service Status:")
        print(f"  {'Service':<30} {'State':<12} {'Latency'}")
        print("  " + "-" * 55)

    active_count = 0
    total_count = len(SERVICES)
    for svc in SERVICES:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", f"{svc}.service"],
            capture_output=True, text=True, timeout=5
        )
        state = result.stdout.strip()
        if state == "active":
            active_count += 1
        
        if not short:
            icon = "●" if state == "active" else "○"
            print(f"  {icon} {svc:<28} {state:<12}")

    # Ollama status
    ollama_ok = False
    try:
        # Run health check in virtual environment where `requests` is available
        check_cmd = [VENV_PY, "-c", "from lib.ollama_client import is_healthy, list_models; print('HEALTHY' if is_healthy() else 'UNHEALTHY'); print(','.join(list_models()[:3]))"]
        res = subprocess.run(check_cmd, capture_output=True, text=True, timeout=5)
        lines = res.stdout.strip().split('\n')
        ollama_ok = len(lines) > 0 and lines[0] == 'HEALTHY'
        
        if not short:
            print(f"\n  Ollama: {'✓ running' if ollama_ok else '✗ offline'}")
            if ollama_ok and len(lines) > 1 and lines[1]:
                print(f"  Loaded models: {lines[1]}")
    except Exception:
        if not short:
            print("  Ollama: (check failed)")

    # Inbox/Review counts for short status
    inbox_count = 0
    review_count = 0
    if short:
        try:
            from lib.knowledge_manager import KnowledgeManager
            km = KnowledgeManager()
            inbox_count = len(km.get_inbox())
            review_dir = BASE_DIR / "review"
            if review_dir.exists():
                review_count = len(list(review_dir.glob("*.md")))
        except Exception:
            pass

    if short:
        status_char = "✓" if ollama_ok else "✗"
        print(f"{status_char}{active_count}/{total_count} | inbox:{inbox_count} | review:{review_count}")
        return

    # Budget status
    try:
        from lib.budget_controller import BudgetController
        bc = BudgetController()
        summary = bc.get_daily_summary()
        pct = (summary['tokens_used'] / bc.config['limits']['daily_tokens']) * 100
        cost_pct = (summary['cost_usd'] / bc.config['limits']['daily_cost_usd']) * 100
        warn_thresh = bc.config['limits']['warning_threshold'] * 100
        
        warn = "⚠️ " if pct >= warn_thresh or cost_pct >= warn_thresh else "✓ "
        print(f"\n  {warn}Budget: {summary['tokens_used']} tokens ({pct:.1f}%), ${summary['cost_usd']:.3f} ({cost_pct:.1f}%)")
        if bc.is_local_only_mode():
            print("  ⚠️ BUDGET EXHAUSTED: Cloud LLMs disabled.")
    except Exception as e:
        print(f"  Budget: (check failed {e})")

    # Swap status
    result = subprocess.run(["free", "-h"], capture_output=True, text=True, timeout=5)
    for line in result.stdout.splitlines():
        if "Swap" in line:
            print(f"  {line.strip()}")

def cmd_uptime():
    print("[Jarvis] Service Uptime:")
    print(f"  {'Service':<30} {'Started At'}")
    print("  " + "-" * 55)
    for svc in SERVICES:
        res = subprocess.run(
            ["systemctl", "--user", "show", "-p", "ActiveEnterTimestamp", "--value", f"{svc}.service"],
            capture_output=True, text=True, timeout=5
        )
        ts = res.stdout.strip()
        if not ts or "0000" in ts:
            ts = "Inactive"
        print(f"  {svc:<30} {ts}")




# ── Pause / Resume ────────────────────────────────────────────────────────────

def get_ollama_pids() -> list[int]:
    try:
        output = subprocess.check_output(["pgrep", "-f", "ollama"], text=True)
        return [int(p) for p in output.strip().split()]
    except subprocess.CalledProcessError:
        return []


def cmd_pause():
    pids = get_ollama_pids()
    if not pids:
        print("Jarvis: Ollama is not running.")
        return
    for pid in pids:
        try:
            os.kill(pid, signal.SIGSTOP)
        except ProcessLookupError:
            pass
        except PermissionError:
            print(f"Jarvis: Permission denied to pause PID {pid}. (Are you running as the same user as Ollama?)")
            return
    with open(BASE_DIR / "logs" / "pause_time.tmp", "w") as f:
        f.write(str(int(time.time())))
    subprocess.run(["notify-send", "Jarvis Paused", "CPU inference suspended."])
    print(f"Jarvis: Paused {len(pids)} Ollama processes.")
    try:
        from lib.event_bus import emit
        emit("system", "paused", {"count": len(pids), "type": "ollama"})
    except Exception:
        pass


def cmd_resume():
    pids = get_ollama_pids()
    if not pids:
        print("Jarvis: Ollama is not running.")
        return
    for pid in pids:
        try:
            os.kill(pid, signal.SIGCONT)
        except ProcessLookupError:
            pass
        except PermissionError:
            print(f"Jarvis: Permission denied to resume PID {pid}.")
            return
    pause_file = BASE_DIR / "logs" / "pause_time.tmp"
    if pause_file.exists():
        pause_file.unlink()
    subprocess.run(["notify-send", "Jarvis Resumed", "AI tasks continuing."])
    print(f"Jarvis: Resumed {len(pids)} Ollama processes.")
    try:
        from lib.event_bus import emit
        emit("system", "resumed", {"count": len(pids), "type": "ollama"})
    except Exception:
        pass


# ── Feedback ──────────────────────────────────────────────────────────────────

def cmd_feedback(rating: str):
    if not HISTORY_PATH.exists():
        print("No history yet.")
        return
    with open(HISTORY_PATH) as f:
        lines = f.readlines()
    if not lines:
        print("No history yet.")
        return
    last = json.loads(lines[-1])
    entry = {**last, "rating": rating, "feedback_ts": datetime.now(timezone.utc).isoformat()}
    with open(FEEDBACK_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"Jarvis: Feedback '{rating}' recorded.")


# ── Backup / Archival ─────────────────────────────────────────────────────────

def cmd_backup(archive=False):
    mode_str = "Archiving" if archive else "Backing up"
    print(f"[Jarvis] {mode_str} code and vault data...")
    
    script_path = REPO_DIR / "bin" / "backup.sh"
    if not script_path.exists():
        print(f"Error: {script_path} not found.")
        return False
    
    cmd = ["bash", str(script_path)]
    if archive:
        cmd.append("--archive")
    
    return subprocess.run(cmd).returncode == 0


# ── Model & API Management ──────────────────────────────────────────────────

def cmd_models():
    print("=== Jarvis Model Configuration ===")
    from lib.ollama_client import list_models, is_healthy
    import tomllib
    
    # Local Models
    if is_healthy():
        try:
            local_models = list_models()
            print(f"\n[Local Ollama] Status: Online")
            print(f"Available: {', '.join(local_models)}")
        except Exception as e:
            print(f"\n[Local Ollama] Error: {e}")
    else:
        print(f"\n[Local Ollama] Status: Offline")

    # Aliases
    config_path = BASE_DIR / "config" / "models.toml"
    if config_path.exists():
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
            print("\n[Aliases (models.toml)]")
            for alias, model in config.get("models", {}).items():
                print(f"  {alias:<10} -> {model}")
    
    # Cloud (OpenRouter)
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        print(f"\n[Cloud OpenRouter] Status: Configured (Key: {key[:8]}...{key[-4:]})")
    else:
        print(f"\n[Cloud OpenRouter] Status: Not Configured")


def cmd_keys():
    print("=== Jarvis API Keys & Environment ===")
    tracked_env = [
        "OPENROUTER_API_KEY",
        "SEARXNG_URL",
        "OLLAMA_BASE_URL",
        "JARVIS_ROOT",
        "PYTHONPATH"
    ]
    for var in tracked_env:
        val = os.environ.get(var, "Not Set")
        if "KEY" in var and val != "Not Set":
            masked = val[:8] + "*" * (len(val) - 12) + val[-4:] if len(val) > 12 else "****"
            print(f"  {var:<20}: {masked}")
        else:
            print(f"  {var:<20}: {val}")


# ── Preferences & Toggles ─────────────────────────────────────────────────────

def load_preferences():
    import tomllib
    pref_path = BASE_DIR / "config" / "preferences.toml"
    if not pref_path.exists():
        return {}
    with open(pref_path, "rb") as f:
        return tomllib.load(f)

def save_preferences(prefs):
    import toml
    pref_path = BASE_DIR / "config" / "preferences.toml"
    with open(pref_path, "w") as f:
        toml.dump(prefs, f)

def cmd_toggle_voice():
    prefs = load_preferences()
    if "preferences" not in prefs:
        prefs["preferences"] = {}
    
    current = prefs["preferences"].get("voice_enabled", True)
    new_state = not current
    prefs["preferences"]["voice_enabled"] = new_state
    
    save_preferences(prefs)
    status = "ENABLED" if new_state else "DISABLED"
    print(f"Jarvis: Voice commands are now {status}.")
    
    # Restart or signal voice_gateway service if needed
    # For now, we just notify
    if new_state:
        print("  Suggested: Run 'systemctl --user start jarvis-voice-gateway' if not running.")
    else:
        print("  Suggested: Run 'systemctl --user stop jarvis-voice-gateway' to release microphone.")


# ── History Logging ───────────────────────────────────────────────────────────

def log_history(user_input: str, intent: str, status: str):
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "input": user_input,
        "intent": intent,
        "status": status,
    }
    with open(HISTORY_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def cmd_knowledge_query(query: str) -> bool:
    print(f"[Jarvis] Analyzing knowledge for: '{query}'...")
    try:
        from lib.semantic_memory import SemanticMemory
        from lib.knowledge_graph import KnowledgeGraph
        from lib.llm import ask, Privacy
        
        # 1. Semantic RAG
        sm = SemanticMemory()
        rag_results = sm.query(query, k=5)
        context_text = "\n\n".join([f"Source: {r.metadata.get('source')}\nContent: {r.content}" for r in rag_results])
        
        # 2. Knowledge Graph
        kg = KnowledgeGraph()
        graph_data = kg.get_related_entities(query)
        graph_text = "\n".join([f"- {g['subject']} --[{g['relation']}]--> {g['object']}" for g in graph_data])
        
        # 3. Synthesis
        prompt = f"""You are Jarvis's knowledge synthesis engine.
Synthesize a comprehensive report about the topic based on the provided Vector Retrieval (RAG) and Knowledge Graph data.

TOPIC: {query}

### GRAHP RELATIONS
{graph_text or "No direct graph relations found."}

### SEMANTIC CONTEXT
{context_text or "No semantic context found."}

Provide a structured, professional report. If facts conflict, note the ambiguity."""

        print("[Jarvis] Synthesizing report...")
        report = ask(task="analyze", messages=[{"role": "user", "content": prompt}], thinking=False)
        print("\n" + "="*60)
        print(f"KNOWLEDGE REPORT: {query}")
        print("="*60)
        print(report)
        print("="*60 + "\n")
        return True
    except Exception as e:
        print(f"[Jarvis] Knowledge query failed: {e}", file=sys.stderr)
        return False


# ── Pipeline Routing ──────────────────────────────────────────────────────────

def route_intent(intent: str, args: dict, user_input: str):
    if intent == "knowledge_graph_query":
        query = args.get("query", "")
        if not query:
            print("Jarvis: What topic should I look up?")
            return False
        return cmd_knowledge_query(query)

    if intent == "clean_document":
        file_path = args.get("file", "")
        if not file_path:
            print("Jarvis: Please specify a file path.")
            return False
        return run_pipeline([VENV_PY, str(BASE_DIR / "tools" / "cleaner.py"), file_path])

    elif intent == "research":
        query = args.get("query", user_input)
        _shadow_require("network_access", f"web search: {query[:60]}")
        return run_pipeline([VENV_PY, str(BASE_DIR / "pipelines" / "research_agent.py"), "--query", query])

    elif intent == "ingest":
        file_path = args.get("file", "")
        if not file_path:
            print("Jarvis: Please specify a file path.")
            return False
        _shadow_require("file_read", f"ingest file: {file_path}")
        return run_pipeline([VENV_PY, str(BASE_DIR / "pipelines" / "ingest.py"), "--once", file_path])

    elif intent == "generate_nix":
        prompt = args.get("query", user_input)
        _shadow_require("file_write", "generate NixOS module")
        _shadow_require("shell_exec", "nixos-rebuild after generate")
        return run_pipeline([
            VENV_PY, str(BASE_DIR / "pipelines" / "agent_loop.py"),
            "--task", "nixos", "--user-prompt", prompt, "--thinking"
        ], timeout=600, risk_level="high")

    elif intent == "optimize_prompt":
        task = args.get("query", "notebooklm")
        return run_pipeline([VENV_PY, str(BASE_DIR / "pipelines" / "optimizer.py"), task])

    elif intent == "validate_nixos":
        _shadow_require("shell_exec", "nixos-rebuild dry-run validation")
        return run_pipeline([VENV_PY, str(BASE_DIR / "lib" / "nix_validator.py"), "--repo", str(BASE_DIR.parent)])

    elif intent == "query_knowledge":
        query = args.get("query", user_input)
        return run_pipeline([VENV_PY, str(BASE_DIR / "pipelines" / "query_knowledge.py"), query])

    elif intent == "query_events":
        try:
            from lib.event_bus import query_events
            events = query_events()
            if not events:
                print("Jarvis: No events today.")
                return True
            print(f"Jarvis: {len(events)} events today:")
            for e in events[:10]:
                print(f"  [{e['source']}] {e['event']}")
            return True
        except Exception as e:
            print(f"Jarvis: Could not query events: {e}")
            return False

    elif intent == "open_dashboard":
        monitor_bin = BASE_DIR / "bin" / "jarvis-monitor"
        if not monitor_bin.exists():
            print("Jarvis: Dashboard binary not found. Building it now, this will take a moment...")
            subprocess.run(["cargo", "build", "--release"], cwd=str(BASE_DIR / "jarvis-monitor"), check=True)
            monitor_bin.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["cp", str(BASE_DIR / "jarvis-monitor" / "target" / "release" / "jarvis-monitor"), str(monitor_bin)], check=True)
        print("Jarvis: Opening dashboard...")
        subprocess.Popen([str(monitor_bin)])
        return True

    elif intent == "start_services":
        cmd_start()
        return True

    elif intent == "stop_services":
        cmd_stop()
        return True

    elif intent == "health_check":
        short = args.get("short", False) or "--short" in user_input
        cmd_status(short=short)
        return True

    elif intent == "refactor":
        query = args.get("query", user_input)
        print(f"[Jarvis] Starting Agentic Refactoring: {query}")
        return run_pipeline([
            VENV_PY, str(BASE_DIR / "pipelines" / "refactor_agent.py"),
            "--query", query
        ], timeout=1800, risk_level="high")

    elif intent == "explain_error":
        query = args.get("query", user_input)
        print(f"[Jarvis] Analyzing Error (Diagnostic Lens): {query}")
        return run_pipeline([
            VENV_PY, str(BASE_DIR / "pipelines" / "agent_loop.py"),
            "--task", "diagnostic", "--user-prompt", query, "--role", "diagnostic", "--thinking"
        ], timeout=600)

    elif intent == "manage_models":
        cmd_models()
        return True

    elif intent == "manage_keys":
        cmd_keys()
        return True

    elif intent == "toggle_voice":
        cmd_toggle_voice()
        return True

    elif intent == "pause":
        cmd_pause()
        return True

    elif intent == "resume":
        cmd_resume()
        return True

    elif intent == "identity":
        query = args.get("query", user_input)
        return run_pipeline([VENV_PY, str(BASE_DIR / "pipelines" / "query_knowledge.py"), query, "--category", "identity"])

    elif intent == "self_improve":
        query = args.get("query", user_input)
        print(f"[Jarvis] Entering self-improvement loop for: {query}")
        return run_pipeline([
            VENV_PY, str(BASE_DIR / "pipelines" / "agent_loop.py"),
            "--task", "self_improvement", "--user-prompt", query, "--role", "coding", "--thinking"
        ], timeout=900, risk_level="high")

    elif intent == "user_profile":
        query = args.get("query", user_input)
        # Check if this is a "remember" (store) or a "query" (discuss)
        store_keywords = ["remember", "store", "save", "my preference is", "i like", "i want", "planning to"]
        is_store = any(k in user_input.lower() for k in store_keywords)
        
        if is_store:
            print(f"[Jarvis] Storing user preference/info: {query}")
            from lib.knowledge_manager import KnowledgeManager
            km = KnowledgeManager()
            km.add_entry(layer=1, content=user_input, category="user_profile", source_title="User Preference", source_url="direct_input")
            print("Jarvis: I will remember that.")
            return True
        else:
            print(f"[Jarvis] Discussing user profile/plans: {query}")
            return run_pipeline([VENV_PY, str(BASE_DIR / "pipelines" / "query_knowledge.py"), query, "--category", "user_profile"])

    elif intent == "ingest_materials":
        query = args.get("query", user_input)
        print(f"[Jarvis] Launching Material Ingestor for: {query}")
        return run_pipeline([
            VENV_PY, str(BASE_DIR / "pipelines" / "material_ingestor.py"),
            "--query", query
        ], timeout=1800)

    elif intent == "learn_language":
        query = args.get("query", user_input)
        print(f"[Jarvis] Starting Assisted Learning Process for: {query}")
        return run_pipeline([
            VENV_PY, str(BASE_DIR / "pipelines" / "language_learner.py"),
            "--query", query
        ], timeout=1800)

    elif intent == "backup":
        return cmd_backup(archive=False)

    elif intent == "archive":
        return cmd_backup(archive=True)

    elif intent == "plan":
        goal = args.get("query", user_input)
        return run_pipeline([VENV_PY, str(BASE_DIR / "pipelines" / "strategist.py"), goal])

    elif intent == "manage_calendar":
        try:
            from lib.calendar_manager import CalendarManager
            cm = CalendarManager()
            if "list" in user_input.lower() or "show" in user_input.lower():
                events = cm.list_events()
                if not events:
                    print("Jarvis: No upcoming events.")
                else:
                    print("Jarvis: Upcoming Events:")
                    for e in events:
                        print(f"  [{e['start_ts'].split('T')[0]}] {e['title']}")
                return True
            else:
                # Basic parsing for "add event X at Y"
                # For now, just add as a simple string logic or ask LLM to parse
                title = args.get("query", user_input)
                # We'll default to tomorrow for now if no time found
                start = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
                cm.add_event(title, start)
                print(f"Jarvis: Event '{title}' scheduled for tomorrow.")
                return True
        except Exception as e:
            print(f"Jarvis: Calendar error: {e}")
            return False

    elif intent == "manage_tasks":
        try:
            from lib.calendar_manager import CalendarManager
            cm = CalendarManager()
            if "list" in user_input.lower() or "show" in user_input.lower() or "tasks" in user_input.lower():
                tasks = cm.list_tasks()
                if not tasks:
                    print("Jarvis: Your todo list is empty.")
                else:
                    print("Jarvis: Your Tasks:")
                    for t in tasks:
                        print(f"  [{t['id']}] {t['title']} (P{t['priority']})")
                return True
            elif "done" in user_input.lower() or "complete" in user_input.lower():
                # Extract task ID
                match = re.search(r'\d+', user_input)
                if match:
                    task_id = int(match.group(0))
                    cm.complete_task(task_id)
                    print(f"Jarvis: Task {task_id} marked as completed.")
                    return True
                else:
                    print("Jarvis: Which task ID should I mark as done?")
                    return False
            else:
                title = args.get("query", user_input)
                cm.add_task(title)
                print(f"Jarvis: Task '{title}' added to your list.")
                return True
        except Exception as e:
            print(f"Jarvis: Task error: {e}")
            return False

    else:
        # Unknown intent — first check identity knowledge base for capabilities
        print(f"Jarvis: I didn't understand '{user_input}'. Searching my capabilities...")
        try:
            # Try a RAG query on 'identity' category first
            # We broaden the search terms for better coverage
            search_query = user_input
            if any(w in user_input.lower() for w in ["what", "can", "do", "capability", "function"]):
                search_query = "capabilities"
            
            from pipelines.query_knowledge import query_knowledge
            # Only return True if it's a specific question that RAG can answer definitively.
            # If it's a command/request for a feature, we let it fall through to evolution.
            is_question = any(w in user_input.lower() for w in ["what", "how", "who", "where", "can you"])
            if is_question:
                if query_knowledge(search_query, category="identity"):
                    return True
            else:
                # If it's not a clear question, we still run RAG but don't return True,
                # allowing it to proceed to the Evolution check.
                query_knowledge(search_query, category="identity")
        except Exception as e:
            print(f"Debug: RAG fallback failed: {e}")
            pass

        print(f"Jarvis: Still unsure. Checking if I can implement this as a new capability...")
        try:
            from lib.llm import ask, Privacy
            
            # 1. Ask if this is a plausible feature
            evolution_prompt = (
                f"User request: '{user_input}'\n"
                f"Jarvis current capabilities: research, coding, documentation, knowledge management, system control.\n"
                f"Is this request a missing software or system capability that Jarvis could potentially implement by modifying his own Python code or system config?\n"
                f"Answer with 'YES: <brief feature spec>' or 'NO'."
            )
            evolution_res = ask(task="classify", privacy=Privacy.INTERNAL, messages=[{"role": "user", "content": evolution_prompt}], thinking=False).strip()
            
            if evolution_res.startswith("YES:"):
                feature_spec = evolution_res[4:].strip()
                print(f"Jarvis: I've formulated a plan to add this as a new capability: \"{feature_spec}\"")
                print(f"[Jarvis] Launching autonomous self-evolution loop...")
                return run_pipeline([
                    VENV_PY, str(BASE_DIR / "pipelines" / "agent_loop.py"),
                    "--task", "self_improvement", 
                    "--user-prompt", f"Implement new capability into jarvis.py and related pipelines: {feature_spec}", 
                    "--role", "coding", "--thinking"
                ], timeout=1200, risk_level="high")
            
            # 2. Fallback to suggestions if not a feature
            suggest_prompt = (
                f"The user typed: '{user_input}'\n"
                f"Available Jarvis commands: clean, research, ingest, write nix module, "
                f"optimize prompt, validate nixos, status, start, stop, pause, resume, dashboard, ingest_materials, user_profile, identity.\n"
                f"Suggest 3 similar commands the user might have meant. Be concise."
            )
            response = ask(task="classify", privacy=Privacy.INTERNAL, messages=[{"role": "user", "content": suggest_prompt}], thinking=False)
            print(f"  Did you mean?\n{response}")
        except Exception as e:
            print(f"Debug: Evolution/Suggestion logic failed: {e}")
            print("  Try: jarvis help")
        return False


# ── Help ──────────────────────────────────────────────────────────────────────

def cmd_help():
    print("Jarvis — Local AI Assistant")
    print("\nUsage: jarvis '<natural language command>'")
    print("       jarvis <subcommand>")
    print("\nSubcommands:")
    print("  status           Show all service health + Ollama state")
    print("  start            Start all daemons (systemctl --user)")
    print("  stop             Stop all daemons")
    print("  pause            Suspend Ollama to free CPU (SIGSTOP)")
    print("  resume           Resume Ollama (SIGCONT)")
    print("  uptime           Show how long services have been running")
    print("  learn <topic>    Assisted language learning for a new language")
    print("  index <root>     Index the codebase for the coding agent RAG")
    print("  query <msg>      Ask a question against the knowledge base")
    print("  inbox            View and manage recommended reading queue")
    print("  knowledge        Inspect 3-Layer knowledge base entries")
    print("  training         Check language competency matrix")
    print("  models           List local models and cloud aliases")
    print("  keys             Manage and verify API keys")
    print("  toggle voice     Enable or disable the voice gateway")
    print("  forget           Clear short-term working memory")
    print("  sessions         List and manage active chat sessions")
    print("  codebases        List indexed codebases")
    print("  config nvim      Specialized Neovim config editing mode")
    print("  config nixos     Specialized NixOS config editing mode")
    print("  man              Show the formal jarvis manual page")
    print("  dashboard        Open the Rust-based TUI monitor")
    print("  backup           Sync code and vault data to /THE_VAULT")
    print("  archive          Create timestamped .tar.gz in ~/Backups")
    print("  thumbs-up        Rate last command positively")
    print("  thumbs-down      Rate last command negatively")
    print("  help             Show this help")
    print("  --version        Show version")
    print("\nNatural Language Examples:")
    print("  jarvis 'clean this pdf for notebooklm'")
    print("  jarvis 'research transformer attention mechanisms'")
    print("  jarvis 'write a nix module for postgresql'")


def sync_assets():
    """Ensure man page and completion scripts are in sync with the codebase."""
    try:
        import shutil
        import hashlib

        def needs_sync(src, dst):
            if not dst.exists(): return True
            try:
                with open(src, "rb") as fsrc, open(dst, "rb") as fdst:
                    return hashlib.md5(fsrc.read()).hexdigest() != hashlib.md5(fdst.read()).hexdigest()
            except Exception:
                return True

        def safe_copy(src: Path, dst: Path):
            """Copy src to dst, removing the destination first if it's read-only
            (can happen when NixOS/home-manager previously wrote it to the store)."""
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                try:
                    dst.unlink()
                except PermissionError:
                    # Nothing we can do if we truly lack permission
                    return False
            shutil.copy2(src, dst)
            # Ensure the file is writable going forward
            dst.chmod(0o644)
            return True

        # 1. Sync Man Page
        src_man = BASE_DIR / "docs" / "jarvis.1"
        target_man = Path.home() / ".local" / "share" / "man" / "man1" / "jarvis.1"
        if src_man.exists() and needs_sync(src_man, target_man):
            safe_copy(src_man, target_man)

        # 2. Sync Completion Script (_jarvis function)
        src_comp = BASE_DIR / "completions" / "_jarvis"
        target_comp = Path.home() / ".zsh" / "plugins" / "jarvis-completions" / "_jarvis"
        if src_comp.exists() and needs_sync(src_comp, target_comp):
            safe_copy(src_comp, target_comp)

        # 3. Sync Plugin Loader (jarvis-completions.plugin.zsh)
        src_loader = BASE_DIR / "completions" / "jarvis-completions.plugin.zsh"
        target_loader = Path.home() / ".zsh" / "plugins" / "jarvis-completions" / "jarvis-completions.plugin.zsh"
        if src_loader.exists() and needs_sync(src_loader, target_loader):
            safe_copy(src_loader, target_loader)

    except Exception as e:
        # Non-fatal: print a warning rather than silently swallowing errors
        print(f"[Jarvis] Warning: asset sync failed: {e}", file=sys.stderr)


# ── Session Management ────────────────────────────────────────────────────────

def _ensure_session_token() -> str:
    """
    Generate (or refresh) the active session token and write it to VAULT_ROOT.
    Called once at CLI startup. Returns the token string.
    """
    vault_root = Path(os.environ.get("VAULT_ROOT", "/THE_VAULT/jarvis"))
    session_file = vault_root / "context" / "active_session_token"
    session_file.parent.mkdir(parents=True, exist_ok=True)
    
    token = _secrets.token_hex(16)
    session_file.write_text(token)
    session_file.chmod(0o600)
    return token


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # P0-3: Write session token on every CLI invocation
    _current_session_token = _ensure_session_token()
    sync_assets()
    start_time = time.time()
    try:
        if len(sys.argv) < 2:
            cmd_help()
            sys.exit(0)

        user_input = " ".join(sys.argv[1:])
        emit("cli", "command_received", {"command": user_input})

        # 1. Direct Address Handling: Strip "Jarvis," or "Jarvis " prefix
        name_pattern = re.compile(r'^jarvis[,:\s]+', re.IGNORECASE)
        if name_pattern.match(user_input):
            user_input = name_pattern.sub('', user_input).strip()
            print(f"[Jarvis] Hello! Processing your request: '{user_input}'")

        command = sys.argv[1]

        if command == "--version":
            print(f"Jarvis version {VERSION}")
            return
        
        # 2. Safety Confirmation for High-Risk Intents
        HIGH_RISK_INTENTS = ["generate_nix", "ingest", "learn_explicit", "index_explicit", "self_improve", "ingest_materials"]

        def confirm_action(reason: str):
            print(f"\n[Jarvis] WARNING: This operation involves {reason}.")
            choice = input("Confirm execution? [y/N]: ").lower().strip()
            return choice == 'y'

        # Direct commands bypassing NLP intent classifier
        command = sys.argv[1]
        
        if command == "codebases":
            import tomllib
            cb_path = BASE_DIR / "config" / "codebases.toml"
            if len(sys.argv) >= 3 and sys.argv[2] in ("add", "remove"):
                # Handle add/remove
                print("[Jarvis] Modifying codebases.toml is currently a manual operation. Open config/codebases.toml to edit.")
                return
            
            if cb_path.exists():
                with open(cb_path, "rb") as f:
                    data = tomllib.load(f).get("codebases", {})
                print("[Jarvis] Tracked Codebases & Privacy Tiers:")
                print(f"  {'Path':<50} {'Tier'}")
                print("  " + "-" * 60)
                for path, tier in data.items():
                    print(f"  {path:<50} {tier}")
            else:
                print("Jarvis: config/codebases.toml not found.")
            return

        if command == "forget":
            from lib.working_memory import WorkingMemory
            WorkingMemory().clear()
            print("[Jarvis] Working memory for the current session has been cleared.")
            return

        if command == "sessions":
            from lib.working_memory import WorkingMemory
            sessions = WorkingMemory().list_sessions()
            if not sessions:
                print("No sessions found.")
                return
            print(f"{'Session ID':<40} {'Turns':<10} {'Tokens':<10} {'Last Active'}")
            print("-" * 80)
            for s in sessions:
                print(f"{s['session_id']:<40} {s['turns']:<10} {s['tokens']:<10} {s['last_active']}")
            return

        if command in ("--version", "-v"):
            print(f"jarvis v{VERSION}")
            return
        if command == "--budget-status":
            from lib.budget_controller import BudgetController
            bc = BudgetController()
            summary = bc.get_daily_summary()
            print("[Jarvis] Budget Status (Daily):")
            print(f"  Tokens Used:  {summary['tokens_used']} / {bc.config['limits']['daily_tokens']}")
            print(f"  Cost (USD):   ${summary['cost_usd']:.4f} / ${bc.config['limits']['daily_cost_usd']:.2f}")
            print(f"  Requests:     {summary['requests_count']}")
            if bc.is_local_only_mode():
                print("  WARNING: Local-only mode active (budget exhausted).")
            return
        if command == "help":
            cmd_help()
            return
        if command == "man":
            man_path = BASE_DIR / "docs" / "jarvis.1"
            if man_path.exists():
                print(f"[Jarvis] Opening manual: {man_path}")
                subprocess.run(["man", "-l", str(man_path)])
            else:
                print(f"Jarvis: Manual not found at {man_path}")
            return
        if command == "--short":
            cmd_status(short=True)
            return
        if command == "start":
            cmd_start()
            log_history(user_input, "start_services", "ok")
            return
        if command == "stop":
            cmd_stop()
            log_history(user_input, "stop_services", "ok")
            return
        if command == "pause":
            cmd_pause()
            log_history(user_input, "pause", "ok")
            return
        if command == "resume":
            cmd_resume()
            log_history(user_input, "resume", "ok")
            return
        if command == "thumbs-up":
            cmd_feedback("positive")
            return
        if command == "thumbs-down":
            cmd_feedback("negative")
            return
        if command == "dashboard":
            monitor_bin = BASE_DIR / "bin" / "jarvis-monitor"
            if not monitor_bin.exists():
                print("Jarvis: Dashboard binary not found. Building it now, this will take a moment...")
                subprocess.run(["cargo", "build", "--release"], cwd=str(BASE_DIR / "jarvis-monitor"), check=True)
                monitor_bin.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run(["cp", str(BASE_DIR / "jarvis-monitor" / "target" / "release" / "jarvis-monitor"), str(monitor_bin)], check=True)
            print("Jarvis: Opening dashboard...")
            os.execv(str(monitor_bin), [str(monitor_bin)])
            return

        if command == "uptime":
            cmd_uptime()
            log_history(user_input, "uptime", "ok")
            return

        if command == "backup":
            cmd_backup(archive=False)
            log_history(user_input, "backup", "ok")
            return

        if command == "archive":
            cmd_backup(archive=True)
            log_history(user_input, "archive", "ok")
            return
        
        # --- New Explicit Commands ---
        if command == "learn":
            if len(sys.argv) < 3:
                print("Usage: jarvis learn <topic>  - to start assisted learning")
                print("       jarvis learn <url/file> [--layer L] [--category C]  - for direct ingestion")
                return
            
            # Check if it's a URL or File Path
            arg2 = sys.argv[2]
            if arg2.startswith("http") or os.path.exists(arg2):
                if not confirm_action("modifying knowledge indexes"): return
                cmd = [VENV_PY, str(BASE_DIR / "pipelines" / "doc_learner.py")] + sys.argv[2:]
                print(f"[Jarvis] Learning into Knowledge Layer...")
            else:
                # Treat as topic for assisted learning
                cmd = [VENV_PY, str(BASE_DIR / "pipelines" / "language_learner.py"), "--query", " ".join(sys.argv[2:])]
                print(f"[Jarvis] Starting Assisted Learning Process...")
            
            env = {**os.environ, "PYTHONPATH": str(BASE_DIR)}
            res = subprocess.run(cmd, env=env)
            log_history(user_input, "learn_explicit", "ok" if res.returncode == 0 else "failed")
            return
        
        if command == "index":
            if not confirm_action("modifying codebase indices"): return
            cmd = [str(BASE_DIR / ".venv" / "bin" / "python"), str(BASE_DIR / "tools" / "index_workspace.py")] + sys.argv[2:]
            env = {**os.environ, "PYTHONPATH": str(BASE_DIR)}
            print(f"[Jarvis] Indexing Codebase for Coding Agent...")
            res = subprocess.run(cmd, env=env)
            log_history(user_input, "index_explicit", "ok" if res.returncode == 0 else "failed")
            return
            
        if command == "knowledge":
            from lib.knowledge_manager import KnowledgeManager
            km = KnowledgeManager()
            if len(sys.argv) > 2 and sys.argv[2] == "list":
                print("[Jarvis] 3-Layer Knowledge Base Entries:")
                import sqlite3
                with sqlite3.connect(km.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    rows = conn.execute("SELECT layer, category, COUNT(*) as count FROM chunks GROUP BY layer, category ORDER BY layer").fetchall()
                    print(f"  {'Layer':<8} {'Category':<20} {'Chunks'}")
                    print("  " + "-" * 40)
                    for r in rows:
                        cat = r['category'] or "None"
                        print(f"  {r['layer']:<8} {cat:<20} {r['count']}")
            elif len(sys.argv) > 2 and sys.argv[2] == "summary":
                print("[Jarvis] Knowledge Summary (Trained Materials):")
                import sqlite3
                with sqlite3.connect(km.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    # Group by base category (e.g., 'python' for 'python_core', 'python_docs')
                    rows = conn.execute("""
                        SELECT 
                            COALESCE(
                                CASE 
                                    WHEN category LIKE '%_core' THEN REPLACE(category, '_core', '')
                                    WHEN category LIKE '%_docs' THEN REPLACE(category, '_docs', '')
                                    WHEN category LIKE '%_theory' THEN REPLACE(category, '_theory', '')
                                    ELSE category 
                                END, 'unknown'
                            ) AS lang,
                            GROUP_CONCAT(DISTINCT layer) as layers
                        FROM chunks 
                        GROUP BY lang
                    """).fetchall()
                    print(f"  {'Language/Tool':<20} {'Layers Trained'}")
                    print("  " + "-" * 35)
                    for r in rows:
                        lang = r['lang'] or "unknown"
                        print(f"  {lang:<20} {r['layers']}")
            else:
                print("Usage: jarvis knowledge [list|summary]")
            return

        if command == "training":
            from lib.knowledge_manager import KnowledgeManager
            km = KnowledgeManager()
            print("[Jarvis] Language Competency (Training Status):")
            import sqlite3
            with sqlite3.connect(km.db_path) as conn:
                conn.row_factory = sqlite3.Row
                langs = ["python", "rust", "nix", "lua", "javascript"]
                print(f"  {'Language':<12} {'Layer 1':<10} {'Layer 2':<10} {'Layer 3':<10}")
                print("  " + "-" * 45)
                for lang in langs:
                    status = []
                    for layer in [1, 2, 3]:
                        cat_map = {1: "_core", 2: "_docs", 3: "_theory"}
                        suffix = cat_map[layer]
                        count = conn.execute("SELECT COUNT(*) FROM chunks WHERE layer = ? AND category = ?", (layer, lang + suffix)).fetchone()[0]
                        status.append("✓" if count > 0 else "✗")
                    print(f"  {lang:<12} {status[0]:<10} {status[1]:<10} {status[2]:<10}")
            return

        if command == "config":
            if len(sys.argv) < 3:
                print("Usage: jarvis config nvim|nixos <task>")
                return
            target = sys.argv[2]
            task = " ".join(sys.argv[3:])
            if not task:
                print(f"Jarvis: Please specify a task for {target} configuration.")
                return

            if target == "nvim":
                print(f"[Jarvis] Entering Specialized Neovim Config Mode...")
                return run_pipeline([
                    VENV_PY, str(BASE_DIR / "pipelines" / "agent_loop.py"),
                    "--task", "nvim_config", "--user-prompt", task, "--role", "coding", "--thinking"
                ], timeout=1200)
            elif target == "nixos":
                print(f"[Jarvis] Entering Specialized NixOS Config Mode...")
                return run_pipeline([
                    VENV_PY, str(BASE_DIR / "pipelines" / "agent_loop.py"),
                    "--task", "nixos_config", "--user-prompt", task, "--role", "coding", "--thinking"
                ], timeout=1200)
            else:
                print(f"Jarvis: Unknown config target '{target}'. Use 'nvim' or 'nixos'.")
            return

        if command == "inbox":
            from lib.knowledge_manager import KnowledgeManager
            km = KnowledgeManager()
            # Extract process <ID>
            if len(sys.argv) >= 4 and sys.argv[2] == "process":
                item_id = sys.argv[3]
                print(f"[Jarvis] Processing NLP material from inbox ID {item_id}...")
                
                with sqlite3.connect(km.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    row = conn.execute("SELECT url FROM inbox WHERE id = ?", (item_id,)).fetchone()
                
                if row and row['url']:
                    path_b = row['url']
                    print(f"  Found file: {path_b}")
                    domain_category = f"pdf_doc_{item_id}"
                    print(f"  Isolating into new domain index: category='{domain_category}'")
                    cmd = [
                        str(BASE_DIR / ".venv" / "bin" / "python"), 
                        str(BASE_DIR / "pipelines" / "doc_learner.py"), 
                        path_b, "--layer", "3", "--category", domain_category
                    ]
                    env = {**os.environ, "PYTHONPATH": str(BASE_DIR)}
                    subprocess.run(cmd, env=env)
                    # Mark done
                    with sqlite3.connect(km.db_path) as conn:
                        conn.execute("UPDATE inbox SET status='completed' WHERE id=?", (item_id,))
                else:
                    print(f"Jarvis: Inbox ID {item_id} not found or has no URL.")
            else:
                print("[Jarvis] Pending Inbox Items:")
                items = km.get_inbox()
                if not items:
                    print("  No pending items.")
                else:
                    print(f"  {'ID':<4} {'Type':<20} {'Title'}")
                    print("  " + "-" * 50)
                    for item in items:
                        itype = item.get('type') or "None"
                        print(f"  {item['id']:<4} {itype:<20} {item['title']}")
            return

        if command == "approve":
            if len(sys.argv) < 3:
                print("Usage: jarvis approve <pending_id>")
                print("       Resolves a pending OOB capability approval.")
                print("       Run 'jarvis pending' to list pending approvals.")
                return
            pending_id = sys.argv[2]
            
            from lib.security.audit import AuditLogger
            from lib.security.grants import CapabilityGrantManager
            from lib.security.context import SecurityContext
            from lib.security.exceptions import CapabilityPending
            
            audit = AuditLogger()
            gm = CapabilityGrantManager(audit_logger=audit)
            
            row = audit.get_pending(pending_id)
            if row is None:
                print(f"[Jarvis] No pending approval found with id: {pending_id}")
                return
            
            cap = row["capability"]
            agent = row["agent_id"]
            reason = row["reason"]
            print(f"\n[Jarvis] Pending approval request:")
            print(f"  Capability : {cap}")
            print(f"  Agent      : {agent}")
            print(f"  Reason     : {reason}")
            print(f"  Pending ID : {pending_id}")
            
            resp = input("\n  Approve? [y/N] ").strip().lower()
            approved = resp in ("y", "yes")
            
            # Use an ADMIN-level context to resolve (only admin can approve)
            admin_ctx = SecurityContext(agent_id="cli-admin", trust_level=3)
            try:
                grant = gm.resolve_pending(pending_id, admin_ctx, approved=approved)
                if approved and grant:
                    print(f"[Jarvis] Approved. Capability '{cap}' granted.")
                else:
                    print(f"[Jarvis] Denied. Capability '{cap}' rejected.")
            except Exception as e:
                print(f"[Jarvis] Error resolving pending grant: {e}", file=sys.stderr)
            
            log_history(user_input, "approve", "ok")
            return

        if command == "pending":
            from lib.security.audit import AuditLogger
            audit = AuditLogger()
            rows = audit.list_pending()
            if not rows:
                print("[Jarvis] No pending capability approvals.")
                return
            print(f"\n[Jarvis] Pending capability approvals ({len(rows)}):\n")
            print(f"  {'ID':<10} {'Agent':<20} {'Capability':<25} {'Reason'}")
            print("  " + "-" * 75)
            for r in rows:
                print(f"  {r['id']:<10} {r['agent_id']:<20} {r['capability']:<25} {r['reason']}")
            print(f"\n  Run: jarvis approve <id>")
            return

        if command == "query":
            query = " ".join(sys.argv[2:])
            if not query:
                print("Usage: jarvis query <question>")
                return
            cmd = [str(BASE_DIR / ".venv" / "bin" / "python"), str(BASE_DIR / "pipelines" / "query_knowledge.py"), query]
            env = {**os.environ, "PYTHONPATH": str(BASE_DIR)}
            res = subprocess.run(cmd, env=env)
            log_history(user_input, "query_explicit", "ok" if res.returncode == 0 else "failed")
            return
        if command == "status":
            short = "--short" in sys.argv
            cmd_status(short=short)
            log_history(user_input, "health_check", "ok")
            return

        if command == "models":
            cmd_models()
            log_history(user_input, "models", "ok")
            return

        if command == "keys":
            cmd_keys()
            log_history(user_input, "keys", "ok")
            return

        if command == "toggle":
            if len(sys.argv) > 2 and sys.argv[2] == "voice":
                cmd_toggle_voice()
            else:
                print("Usage: jarvis toggle voice")
            log_history(user_input, "toggle", "ok")
            return

        if command == "completion":
            if len(sys.argv) < 3: return
            ctype = sys.argv[2]
            if ctype == "commands":
            # List all top-level subcommands with descriptions for Zsh
                commands = {
                    "start": "Start all background services",
                    "stop": "Stop all background services",
                    "status": "Show service health and model status",
                    "uptime": "Show how long each service has been running",
                    "pause": "Suspend AI inference (SIGSTOP Ollama)",
                    "resume": "Resume AI inference (SIGCONT Ollama)",
                    "learn": "Assisted language learning or direct ingestion",
                    "index": "Index the codebase for the coding agent RAG",
                    "query": "Ask a question against the knowledge base",
                    "inbox": "View and manage the recommended reading queue",
                    "knowledge": "Inspect 3-Layer knowledge base entries",
                    "training": "Show language competency matrix",
                    "config": "Specialized configuration editing mode (nvim|nixos)",
                    "man": "Show the formal jarvis manual page",
                    "dashboard": "Open the Rust-based TUI monitor",
                    "backup": "Sync code and vault data to storage",
                    "archive": "Create a timestamped .tar.gz backup",
                    "thumbs-up": "Give positive feedback on the last command",
                    "thumbs-down": "Give negative feedback on the last command",
                    "models": "List local models and cloud aliases",
                    "keys": "Manage and verify API keys",
                    "toggle": "Toggle system preferences (voice, etc.)",
                    "forget": "Clear short-term working memory",
                    "sessions": "List and manage active chat sessions",
                    "codebases": "List indexed codebases",
                    "approve": "Approve a pending OOB capability grant",
                    "pending": "List pending capability approval requests",
                    "help": "Show usage help"
                }
                for cmd, desc in sorted(commands.items()):
                    print(f"{cmd}:{desc}")
            elif ctype == "categories":
                from lib.knowledge_manager import KnowledgeManager
                import sqlite3
                km = KnowledgeManager()
                with sqlite3.connect(km.db_path) as conn:
                    rows = conn.execute("SELECT DISTINCT category FROM chunks").fetchall()
                    for r in rows: print(r[0])
            elif ctype == "models":
                from lib.ollama_client import list_models
                import tomllib
                # Local models
                for m in list_models(): print(m)
                # Aliases from config
                conf_path = BASE_DIR / "config" / "models.toml"
                if conf_path.exists():
                    with open(conf_path, "rb") as f:
                        data = tomllib.load(f).get("models", {})
                        for alias in data.keys(): print(alias)
            elif ctype == "sessions":
                from lib.working_memory import WorkingMemory
                for s in WorkingMemory().list_sessions():
                    print(s['session_id'])
            elif ctype == "inbox":
                from lib.knowledge_manager import KnowledgeManager
                km = KnowledgeManager()
                for item in km.get_inbox():
                    print(item['id'])
            return

        # Natural language routing
        print(f"[Jarvis] Classifying: '{user_input}'...")
        result = classify_intent(user_input)
        intent = result.get("intent", "unknown")
        args = result.get("args", {})
        print(f"[Jarvis] Intent: {intent}")

        # Risk Assessment
        if intent in HIGH_RISK_INTENTS:
            risk_map = {
                "generate_nix": "modifying NixOS configuration (roles)",
                "ingest": "modifying knowledge indexes",
                "identity": "modifying system identity knowledge",
                "self_improve": "modifying the Jarvis codebase directly"
            }
            if not confirm_action(risk_map.get(intent, "modifying system components")):
                print("Jarvis: Operation cancelled by user.")
                return

        success = route_intent(intent, args, user_input)
        log_history(user_input, intent, "ok" if success else "failed")
    finally:
        if "completion" not in sys.argv:
            duration = time.time() - start_time
            print(f"\n[Jarvis] Stats: Response took {duration:.2f}s")


if __name__ == "__main__":
    main()
