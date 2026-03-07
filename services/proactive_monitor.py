#!/usr/bin/env python3
"""
Proactive Monitoring & Self-Healing Service (Phase 7.2)
/home/qwerty/NixOSenv/Jarvis/services/proactive_monitor.py

Background service that analyzes events, detects anomalies,
and triggers autonomous fixes when possible.
"""

import os
import sys
import time
import json
import subprocess
import re
from pathlib import Path
from datetime import datetime, timezone

# Runtime paths
BASE_DIR = Path(os.environ.get("JARVIS_ROOT", Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(BASE_DIR))

try:
    from lib.event_bus import query_today, emit
    from lib.ollama_client import chat, is_healthy, OllamaError
    from lib.model_router import route
except ImportError:
    # Fallback for direct execution
    sys.path.append(os.getcwd())
    from lib.event_bus import query_today, emit
    from lib.ollama_client import chat, is_healthy, OllamaError
    from lib.model_router import route

MONITOR_INTERVAL = 300  # 5 minutes
FAIL_THRESHOLD = 3      # Number of recent errors to trigger analysis

ANALYSIS_PROMPT = """You are the Jarvis Proactive Monitor. Analyze the following recent system events for patterns of failure or inefficiency.

Recent Events:
{events_text}

Is there a systemic issue here that Jarvis can fix automatically? 
If YES, provide a JSON response with "issue", "diagnosis", "seriousness", and "action".
Possible actions: "fix_nixos", "restart_ollama", "optimize_prompt", or "none".

Response format:
JSON object only. Example: {{"issue": "NixOS validation failing", "diagnosis": "missing attribute 'pkgs.lib'", "seriousness": "high", "action": "fix_nixos"}}

Only suggest "none" if no issue is detected or no clear action can be taken."""

def get_recent_events(minutes=30):
    all_today = query_today()
    now_ts = datetime.now(timezone.utc)
    recent = []
    for e in all_today:
        try:
            e_ts = datetime.fromisoformat(e['ts'])
            if (now_ts - e_ts).total_seconds() < minutes * 60:
                recent.append(e)
        except ValueError:
            continue
    return recent

def analyze_health():
    recent = get_recent_events(30)
    errors = [e for e in recent if e['level'] in ('WARN', 'ERROR')]
    
    if len(errors) < FAIL_THRESHOLD:
        print(f"[Monitor] Found {len(errors)} errors in last 30m. Threshold not met ({FAIL_THRESHOLD}).")
        return
        
    print(f"[Monitor] Investigating {len(errors)} errors...")
    events_text = "\n".join([f"[{e['ts']}] {e['source']}.{e['event']}: {e['details']}" for e in recent])
    
    messages = [{"role": "user", "content": ANALYSIS_PROMPT.format(events_text=events_text)}]
    
    try:
        decision = route("classify")
        response = chat(
            model_alias=decision.model_alias,
            messages=messages,
            thinking=False,
            temperature=0.0
        )
        
        # Extract JSON
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if not match:
            print(f"[Monitor] Could not parse analysis from response: {response[:100]}")
            return
            
        analysis = json.loads(match.group(0))
        if analysis.get("action") == "none":
            print("[Monitor] No systemic issue detected.")
            return
            
        print(f"[Monitor] ALERT: {analysis['issue']} Detected!")
        emit("monitor", "alert", analysis, level="WARN")
        
        trigger_fix(analysis)
    except Exception as e:
        print(f"[Monitor] Analysis failed: {e}")

def trigger_fix(analysis):
    action = analysis.get("action")
    print(f"[Monitor] Triggering autonomous action: {action}")
    
    jarvis_bin = str(BASE_DIR / "jarvis.py")
    venv_py = str(BASE_DIR / ".venv" / "bin" / "python")
    
    env = {**os.environ, "PYTHONPATH": str(BASE_DIR)}
    
    if action == "fix_nixos":
        print(f"[Monitor] Triggering autonomous NixOS fix...")
        # We wrap it in a goal for strategist or run agent_loop directly
        cmd = [venv_py, jarvis_bin, f"fix the following NixOS error: {analysis.get('diagnosis')}"]
        subprocess.run(cmd, env=env)
    elif action == "restart_ollama":
        print(f"[Monitor] Restarting Ollama service...")
        # Since we use systemctl --user, we might need a wrapper or assume permission
        subprocess.run(["systemctl", "--user", "restart", "ollama"])
    elif action == "optimize_prompt":
        print(f"[Monitor] Triggering prompt optimizer...")
        # Extract task name from diagnosis or issue if possible, else default
        task = "notebooklm" # Default for now
        cmd = [venv_py, jarvis_bin, f"optimize the prompt for {task}"]
        subprocess.run(cmd, env=env)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Jarvis Proactive Monitor")
    parser.add_argument("--once", action="store_true", help="Run analysis once and exit")
    args = parser.parse_args()

    if args.once:
        print("[Monitor] Running single analysis cycle...")
        analyze_health()
        return

    print("[Monitor] Proactive Monitor Started. Interval: 300s.")
    emit("monitor", "startup", {"interval": MONITOR_INTERVAL})
    
    while True:
        try:
            analyze_health()
        except Exception as e:
            print(f"[Monitor] Error in analysis loop: {e}")
        
        time.sleep(MONITOR_INTERVAL)

if __name__ == "__main__":
    main()
