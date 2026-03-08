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
import argparse
import signal
import httpx
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path(os.environ.get("JARVIS_ROOT", Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(BASE_DIR))
from lib.event_bus import emit
from lib.snapshot_manager import SnapshotManager

# Configuration
CHECK_INTERVAL = 60  # seconds
MAX_RESTARTS_PER_HOUR = 3
LSP_URL = "http://127.0.0.1:8001"
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
            capture_output=True, text=True, timeout=5
        )
        return res.stdout.strip() == "active"
    except Exception:
        return False

def request_approval(service_name, reason):
    """Request permission to restart a service via the LSP security bridge."""
    print(f"[Self-Heal] Requesting OOB approval for {service_name}...")
    try:
        # Request OOB grant
        resp = httpx.post(f"{LSP_URL}/security/request", json={
            "capability": f"service:restart:{service_name}",
            "reason": reason,
            "scope": "task"
        }, timeout=5.0)
        data = resp.json()
        
        if data.get("granted"):
            return True
            
        pending_id = data.get("pending_id")
        if not pending_id:
            print(f"[Self-Heal] Request denied or failed: {data.get('error')}")
            return False
            
        # For the bootstrap phase, we don't block the daemon indefinitely.
        # We just log that it's pending and return False to prevent autonomous restart.
        print(f"[Self-Heal] Restart pending approval (ID: {pending_id}). Run 'jarvis approve {pending_id}'.")
        return False 
    except Exception as e:
        print(f"[Self-Heal] LSP bridge unavailable for approval: {e}")
        return False

def _attempt_snapshot_rollback(service_name: str) -> bool:
    """
    Attempt to restore the most recent available snapshot.
    Called when a service has exceeded the restart limit after a config change.
    
    Args:
        service_name: The service that triggered the rollback (for logging).
    
    Returns:
        True if a snapshot was restored, False otherwise.
    """
    sm = SnapshotManager(BASE_DIR)
    snapshots = sm.list_snapshots()
    if not snapshots:
        print(f"[Self-Heal] No snapshots available for rollback.")
        emit("self_healer", "rollback_failed", {"service": service_name, "reason": "no_snapshots"})
        return False
    
    latest = snapshots[0]  # list_snapshots returns sorted descending by time
    snapshot_name = latest["name"]
    print(f"[Self-Heal] Attempting rollback to snapshot: {snapshot_name}")
    emit("self_healer", "rollback_initiated", {"service": service_name, "snapshot": snapshot_name})
    
    if sm.restore_snapshot(snapshot_name):
        print(f"[Self-Heal] Rollback successful. Restart {service_name} to apply.")
        emit("self_healer", "rollback_success", {"service": service_name, "snapshot": snapshot_name})
        return True
    else:
        print(f"[Self-Heal] Rollback failed: snapshot {snapshot_name} not found.")
        emit("self_healer", "rollback_failed", {"service": service_name, "snapshot": snapshot_name})
        return False

def restart_service(service_name, dry_run=False):
    """Attempt to restart a service if within limits."""
    now = datetime.now()
    history = RESTART_HISTORY.get(service_name, [])
    # Cleanup history
    history = [t for t in history if t > now - timedelta(hours=1)]
    RESTART_HISTORY[service_name] = history

    if len(history) >= MAX_RESTARTS_PER_HOUR:
        print(f"[Self-Heal] CRITICAL: Max restarts reached for {service_name}. Attempting snapshot rollback...")
        emit("self_healer", "critical_failure", {"service": service_name, "reason": "restart_limit_reached"})
        _attempt_snapshot_rollback(service_name)
        return False

    # Safety: If it's already failed once this hour, require OOB approval
    if len(history) >= 1:
        if not request_approval(service_name, f"Service failed again after recent restart. (History: {len(history)} restat/hr)"):
            return False

    if dry_run:
        print(f"[Self-Heal] [DRY-RUN] Would restart {service_name}")
        return True

    print(f"[Self-Heal] Attempting to restart {service_name}...")
    try:
        subprocess.run(["systemctl", "--user", "restart", service_name], check=True, timeout=10)
        RESTART_HISTORY[service_name].append(now)
        emit("self_healer", "service_restarted", {"service": service_name})
        return True
    except Exception as e:
        print(f"[Self-Heal] Failed to restart {service_name}: {e}")
        emit("self_healer", "restart_failed", {"service": service_name, "error": str(e)})
        return False

def main():
    parser = argparse.ArgumentParser(description="Jarvis Self-Healer Daemon")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually restart services")
    args = parser.parse_args()

    print(f"[Self-Heal] Daemon started. (Dry-run: {args.dry_run})")
    emit("self_healer", "started", {"dry_run": args.dry_run})
    
    while True:
        for service in SERVICES:
            if not get_service_status(service):
                print(f"[Self-Heal] {service} is DOWN.")
                restart_service(service, dry_run=args.dry_run)
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[Self-Healer] Stopped.")
        emit("self_healer", "stopped")
