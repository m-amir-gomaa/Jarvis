#!/usr/bin/env python3
"""
MVP BIG — Jarvis Unified CLI
/THE_VAULT/jarvis/jarvis.py  (extended with full routing)

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
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/THE_VAULT/jarvis")

BASE_DIR = Path("/THE_VAULT/jarvis")
HISTORY_PATH = BASE_DIR / "logs" / "history.jsonl"
FEEDBACK_PATH = BASE_DIR / "logs" / "feedback.jsonl"
VERSION = "0.1.0"

SERVICES = [
    "jarvis-health-monitor",
    "jarvis-git-monitor",
    "jarvis-coding-agent",
]

INTENT_PROMPT = """You are an intent classifier for a command-line AI assistant.
Classify the user input into exactly ONE of these intents and respond with valid JSON only.

Intents:
- clean_document: clean/process a PDF or markdown file
- research: research a topic online
- ingest: add a file to the knowledge base
- generate_nix: write or fix a NixOS module or config
- optimize_prompt: improve a prompt for a task
- validate_nixos: check NixOS configuration for errors
- git_summary: summarize recent git commits
- query_knowledge: ask a question about the knowledge base
- query_events: ask what happened today/this week
- open_dashboard: open the TUI dashboard
- start_services: start all background services
- stop_services: stop all background services
- health_check: check system status
- pause: pause AI inference
- resume: resume AI inference
- unknown: none of the above

Response format (JSON only, no other text):
{"intent": "<intent>", "args": {"file": "<file if mentioned>", "query": "<query if applicable>"}}

User input: """


# ── Intent Classification ─────────────────────────────────────────────────────

def classify_intent(user_input: str) -> dict:
    try:
        from lib.ollama_client import chat, is_healthy
        from lib.model_router import route

        if not is_healthy():
            return {"intent": "unknown", "args": {}}

        messages = [{"role": "user", "content": INTENT_PROMPT + user_input}]
        response = chat(route("classify"), messages, thinking=False, temperature=0.1)

        # Extract JSON from response
        match = re.search(r'\{.*\}', response, re.DOTALL)
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


def cmd_status():
    print("[Jarvis] Service Status:")
    print(f"  {'Service':<30} {'State':<12} {'Latency'}")
    print("  " + "-" * 55)

    for svc in SERVICES:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", f"{svc}.service"],
            capture_output=True, text=True, timeout=5
        )
        state = result.stdout.strip()
        icon = "●" if state == "active" else "○"
        print(f"  {icon} {svc:<28} {state:<12}")

    # Ollama status
    try:
        from lib.ollama_client import is_healthy, list_models
        ollama_ok = is_healthy()
        models = list_models() if ollama_ok else []
        print(f"\n  Ollama: {'✓ running' if ollama_ok else '✗ offline'}")
        if models:
            print(f"  Loaded models: {', '.join(models[:3])}")
    except Exception:
        print("  Ollama: (check failed)")

    # Swap status
    result = subprocess.run(["free", "-h"], capture_output=True, text=True, timeout=5)
    for line in result.stdout.splitlines():
        if "Swap" in line:
            print(f"  {line.strip()}")


def cmd_short_status() -> str:
    """One-liner for Waybar integration."""
    active = 0
    for svc in SERVICES:
        res = subprocess.run(
            ["systemctl", "--user", "is-active", f"{svc}.service"],
            capture_output=True, text=True, timeout=3
        )
        if res.stdout.strip() == "active":
            active += 1
    return f"Jarvis {active}/{len(SERVICES)}"


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
    with open(BASE_DIR / "logs" / "pause_time.tmp", "w") as f:
        f.write(str(int(time.time())))
    subprocess.run(["notify-send", "Jarvis Paused", "CPU inference suspended."])
    print(f"Jarvis: Paused {len(pids)} Ollama processes.")


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
    pause_file = BASE_DIR / "logs" / "pause_time.tmp"
    if pause_file.exists():
        pause_file.unlink()
    subprocess.run(["notify-send", "Jarvis Resumed", "AI tasks continuing."])
    print(f"Jarvis: Resumed {len(pids)} Ollama processes.")


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


# ── Pipeline Routing ──────────────────────────────────────────────────────────

def route_intent(intent: str, args: dict, user_input: str):
    VENV_PY = str(BASE_DIR / ".venv" / "bin" / "python")
    env = {**os.environ, "PYTHONPATH": str(BASE_DIR)}

    def run_pipeline(cmd: list, timeout: int = 300):
        result = subprocess.run(cmd, env=env, timeout=timeout)
        return result.returncode == 0

    if intent == "clean_document":
        file_path = args.get("file", "")
        if not file_path:
            print("Jarvis: Please specify a file path.")
            return False
        return run_pipeline([VENV_PY, str(BASE_DIR / "tools" / "cleaner.py"), file_path])

    elif intent == "research":
        query = args.get("query", user_input)
        return run_pipeline([VENV_PY, str(BASE_DIR / "pipelines" / "research_agent.py"), "--query", query])

    elif intent == "ingest":
        file_path = args.get("file", "")
        if not file_path:
            print("Jarvis: Please specify a file path.")
            return False
        return run_pipeline([VENV_PY, str(BASE_DIR / "pipelines" / "ingest.py"), "--once", file_path])

    elif intent == "generate_nix":
        prompt = args.get("query", user_input)
        return run_pipeline([
            VENV_PY, str(BASE_DIR / "pipelines" / "agent_loop.py"),
            "--task", "nixos", "--user-prompt", prompt, "--thinking"
        ], timeout=600)

    elif intent == "optimize_prompt":
        task = args.get("query", "notebooklm")
        return run_pipeline([VENV_PY, str(BASE_DIR / "pipelines" / "optimizer.py"), task])

    elif intent == "validate_nixos":
        return run_pipeline([VENV_PY, str(BASE_DIR / "lib" / "nix_validator.py"), "--repo", "/home/qwerty/NixOSenv"])

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
        subprocess.Popen([str(BASE_DIR / "bin" / "jarvis-monitor")])
        print("Jarvis: Opening dashboard...")
        return True

    elif intent == "start_services":
        cmd_start()
        return True

    elif intent == "stop_services":
        cmd_stop()
        return True

    elif intent == "health_check":
        cmd_status()
        return True

    elif intent == "pause":
        cmd_pause()
        return True

    elif intent == "resume":
        cmd_resume()
        return True

    else:
        # Unknown intent — suggest 3 alternatives via Ollama
        print(f"Jarvis: I didn't understand '{user_input}'. Thinking of alternatives...")
        try:
            from lib.ollama_client import chat
            from lib.model_router import route
            suggest_prompt = (
                f"The user typed: '{user_input}'\n"
                f"Available Jarvis commands: clean, research, ingest, write nix module, "
                f"optimize prompt, validate nixos, status, start, stop, pause, resume, dashboard.\n"
                f"Suggest 3 similar commands the user might have meant. Be concise."
            )
            response = chat(route("classify"), [{"role": "user", "content": suggest_prompt}], thinking=False)
            print(f"  Did you mean?\n{response}")
        except Exception:
            print("  Try: jarvis help")
        return False


# ── Help ──────────────────────────────────────────────────────────────────────

def cmd_help():
    print("""Jarvis — Local AI Assistant

Usage: jarvis '<natural language command>'
       jarvis <subcommand>

Subcommands:
  status           Show all service health + Ollama state
  start            Start all daemons (systemctl --user)
  stop             Stop all daemons
  pause            Suspend Ollama to free CPU (SIGSTOP)
  resume           Resume Ollama (SIGCONT)
  thumbs-up        Rate last command positively
  thumbs-down      Rate last command negatively
  help             Show this help
  --version        Show version

Natural Language Examples:
  jarvis 'clean this pdf for notebooklm'
  jarvis 'research transformer attention mechanisms'
  jarvis 'add /path/to/paper.pdf to my knowledge base'
  jarvis 'write a nix module for postgresql'
  jarvis 'validate my nixos config'
  jarvis 'what happened today'
  jarvis 'open dashboard'
""")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        cmd_help()
        sys.exit(0)

    user_input = " ".join(sys.argv[1:])

    # Direct commands bypassing NLP intent classifier
    command = sys.argv[1]
    
    if command in ("--version", "-v"):
        print(f"jarvis v{VERSION}")
        return
    if command == "help":
        cmd_help()
        return
    if command == "status":
        cmd_status()
        log_history(user_input, "health_check", "ok")
        return
    if command == "--short":
        print(cmd_short_status())
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
        monitor_bin = str(BASE_DIR / "bin" / "jarvis-monitor")
        print("Jarvis: Opening dashboard...")
        os.execv(monitor_bin, [monitor_bin])
        return
    
    # --- New Explicit Commands ---
    if command == "learn":
        # e.g., jarvis learn URL/FILE [--layer 1] [--category docs]
        cmd = [str(BASE_DIR / ".venv" / "bin" / "python"), str(BASE_DIR / "pipelines" / "doc_learner.py")] + sys.argv[2:]
        env = {**os.environ, "PYTHONPATH": str(BASE_DIR)}
        print(f"[Jarvis] Learning into Knowledge Layer...")
        res = subprocess.run(cmd, env=env)
        log_history(user_input, "learn_explicit", "ok" if res.returncode == 0 else "failed")
        return
    
    if command == "index":
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
            with km.db_path.open() as f: pass # Ensure DB exists
            import sqlite3
            with sqlite3.connect(km.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute("SELECT layer, category, COUNT(*) as count FROM chunks GROUP BY layer, category ORDER BY layer").fetchall()
                print(f"  {'Layer':<8} {'Category':<20} {'Chunks'}")
                print("  " + "-" * 40)
                for r in rows:
                    cat = r['category'] or "None"
                    print(f"  {r['layer']:<8} {cat:<20} {r['count']}")
        else:
            print("Usage: jarvis knowledge list")
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

    # Natural language routing
    print(f"[Jarvis] Classifying: '{user_input}'...")
    result = classify_intent(user_input)
    intent = result.get("intent", "unknown")
    args = result.get("args", {})
    print(f"[Jarvis] Intent: {intent}")

    success = route_intent(intent, args, user_input)
    log_history(user_input, intent, "ok" if success else "failed")


if __name__ == "__main__":
    main()
