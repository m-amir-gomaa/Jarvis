#!/usr/bin/env python3
"""
benchmarks/system_analysis/check_services.py
Real systemd --user service status — no simulated values.
"""
import json
import subprocess
from datetime import datetime


JARVIS_SERVICES = [
    "jarvis-health-monitor",
    "jarvis-git-monitor",
    "jarvis-coding-agent",
    "jarvis-self-healer",
    "jarvis-lsp",
    "jarvis-voice-gateway",
    "jarvis-daily-digest",
    "jarvis-context-updater",
]


def _systemctl_property(service: str, prop: str, default: str = "unknown") -> str:
    try:
        result = subprocess.run(
            ["systemctl", "--user", "show", service, f"--property={prop}", "--value"],
            capture_output=True, text=True, timeout=5
        )
        val = result.stdout.strip()
        return val if val else default
    except Exception:
        return default


def check_services() -> dict:
    services = {}
    for svc in JARVIS_SERVICES:
        unit = f"{svc}.service"
        active_state = _systemctl_property(unit, "ActiveState")
        sub_state = _systemctl_property(unit, "SubState")
        load_state = _systemctl_property(unit, "LoadState")
        exec_main_pid = _systemctl_property(unit, "ExecMainPID", "0")
        active_enter_ts = _systemctl_property(unit, "ActiveEnterTimestamp", "")
        result_prop = _systemctl_property(unit, "Result", "")

        # Calculate uptime if active
        uptime_str = "n/a"
        if active_state == "active" and active_enter_ts and active_enter_ts != "0":
            try:
                # Systemd timestamp format: "Sun 2026-03-08 10:00:00 EET"
                # Parse with dateutil or strptime fallback
                ts_clean = " ".join(active_enter_ts.split()[1:3])  # drop weekday
                entered = datetime.strptime(ts_clean, "%Y-%m-%d %H:%M:%S")
                delta = datetime.now() - entered
                hours, rem = divmod(int(delta.total_seconds()), 3600)
                minutes = rem // 60
                uptime_str = f"{hours}h {minutes}m"
            except Exception:
                uptime_str = "parse_error"

        services[svc] = {
            "active_state": active_state,
            "sub_state": sub_state,
            "load_state": load_state,
            "pid": exec_main_pid if exec_main_pid != "0" else None,
            "uptime": uptime_str,
            "last_result": result_prop,
            "healthy": active_state == "active" and sub_state == "running",
        }

    # Also check Ollama (system service, not user)
    try:
        ollama_out = subprocess.run(
            ["systemctl", "is-active", "ollama"],
            capture_output=True, text=True, timeout=5
        ).stdout.strip()
        services["ollama"] = {"active_state": ollama_out, "healthy": ollama_out == "active"}
    except Exception:
        services["ollama"] = {"active_state": "unknown", "healthy": False}

    summary = {
        "total": len(JARVIS_SERVICES),
        "healthy": sum(1 for s in JARVIS_SERVICES if services.get(s, {}).get("healthy")),
        "degraded": sum(1 for s in JARVIS_SERVICES if not services.get(s, {}).get("healthy")),
    }

    return {"summary": summary, "services": services}


if __name__ == "__main__":
    data = check_services()
    print(json.dumps(data, indent=2))
