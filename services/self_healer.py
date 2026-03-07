#!/usr/bin/env python3
"""
Jarvis Self-Healer Daemon
/home/qwerty/NixOSenv/Jarvis/services/self_healer.py

Monitors the Jarvis Event Bus for service failures or unresponsiveness
and attempts to restart them via systemd --user.
"""

import os
import sys
import time
import subprocess
import json
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path(os.environ.get("JARVIS_ROOT", Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(BASE_DIR))
from lib.event_bus import emit, query_today

# Configuration
CHECK_INTERVAL = 60  # seconds
MAX_RESTARTS_PER_HOUR = 3
SERVICES = [
    "jarvis-coding-agent.service",
    "jarvis-git-monitor.service",
    "jarvis-health-monitor.service"
]

RESTART_HISTORY = {}  # service_name -> [timestamps]

def get_service_status(service_name):
    """Check if a systemd --user service is running."""
    try:
        res = subprocess.run(
            ["systemctl", "--user", "is-active", service_name],
            capture_output=True, text=True
        )
        return res.stdout.strip() == "active"
    except Exception:
        return False

def restart_service(service_name):
    """Attempt to restart a service if within limits."""
    now = datetime.now()
    history = RESTART_HISTORY.get(service_name, [])
    # Cleanup history
    history = [t for t in history if t > now - timedelta(hours=1)]
    RESTART_HISTORY[service_name] = history

    if len(history) >= MAX_RESTARTS_PER_HOUR:
        print(f"[Self-Heal] CRITICAL: Max restarts reached for {service_name}. Manual intervention required.")
        emit("self_healer", "critical_failure", {"service": service_name, "reason": "restart_limit_reached"})
        return False

    print(f"[Self-Heal] Attempting to restart {service_name}...")
    try:
        subprocess.run(["systemctl", "--user", "restart", service_name], check=True)
        RESTART_HISTORY[service_name].append(now)
        emit("self_healer", "service_restarted", {"service": service_name})
        return True
    except subprocess.CalledProcessError as e:
        print(f"[Self-Heal] Failed to restart {service_name}: {e}")
        emit("self_healer", "restart_failed", {"service": service_name, "error": str(e)})
        return False

def check_event_bus_health():
    """Check if services are emitting events."""
    # This is a bit more complex, for now we check if any 'started' or activity event
    # from core services has happened in the last 10 minutes.
    # If not, and the service is 'active' in systemd, it might be hung.
    pass

def main():
    print("[Self-Heal] Daemon started.")
    emit("self_healer", "started")
    
    while True:
        for service in SERVICES:
            if not get_service_status(service):
                print(f"[Self-Heal] {service} is DOWN.")
                restart_service(service)
            else:
                # Optionally check if it's hung (no activity in X minutes)
                # This would require more granular event bus querying
                pass
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[Self-Heal] Stopped.")
        emit("self_healer", "stopped")
