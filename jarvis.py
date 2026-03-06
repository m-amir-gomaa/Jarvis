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
    "jarvis-ingest",
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

    # Direct subcommands (no Ollama needed)
    if user_input in ("--version", "-v"):
        print(f"jarvis v{VERSION}")
        return
    if user_input == "help":
        cmd_help()
        return
    if user_input == "status":
        cmd_status()
        log_history(user_input, "health_check", "ok")
        return
    if user_input == "--short":
        print(cmd_short_status())
        return
    if user_input == "start":
        cmd_start()
        log_history(user_input, "start_services", "ok")
        return
    if user_input == "stop":
        cmd_stop()
        log_history(user_input, "stop_services", "ok")
        return
    if user_input == "pause":
        cmd_pause()
        log_history(user_input, "pause", "ok")
        return
    if user_input == "resume":
        cmd_resume()
        log_history(user_input, "resume", "ok")
        return
    if user_input == "thumbs-up":
        cmd_feedback("positive")
        return
    if user_input == "thumbs-down":
        cmd_feedback("negative")
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
