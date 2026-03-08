#!/usr/bin/env python3
"""
benchmarks/system_analysis/check_security.py
Real security state check — pending grants, session validity, audit log tail.
"""
import json
import sqlite3
import time
from pathlib import Path

VAULT = Path("/THE_VAULT/jarvis")
AUDIT_DB = VAULT / "databases" / "security_audit.db"
SESSION_TOKEN = VAULT / "context" / "active_session_token"


def check_security() -> dict:
    result = {}

    # Session token validity
    if SESSION_TOKEN.exists():
        stat = SESSION_TOKEN.stat()
        age_seconds = time.time() - stat.st_mtime
        result["session_token"] = {
            "exists": True,
            "age_seconds": round(age_seconds, 0),
            "age_human": _human_age(age_seconds),
            "valid": age_seconds < 86400,  # 24h
        }
    else:
        result["session_token"] = {"exists": False, "valid": False}

    # Pending capability grants
    pending = []
    audit_tail = []
    if AUDIT_DB.exists():
        try:
            with sqlite3.connect(str(AUDIT_DB)) as conn:
                conn.row_factory = sqlite3.Row
                # Pending grants
                try:
                    rows = conn.execute(
                        "SELECT id, capability, requested_by, created_at FROM pending_grants ORDER BY created_at DESC LIMIT 20"
                    ).fetchall()
                    pending = [dict(r) for r in rows]
                except Exception as e:
                    pending = [{"error": str(e)}]

                # Audit log tail
                try:
                    rows = conn.execute(
                        "SELECT id, action, capability, outcome, timestamp FROM audit_log ORDER BY timestamp DESC LIMIT 10"
                    ).fetchall()
                    audit_tail = [dict(r) for r in rows]
                except Exception as e:
                    audit_tail = [{"error": str(e)}]
        except Exception as e:
            result["audit_db_error"] = str(e)

    result["pending_grants"] = {
        "count": len(pending),
        "items": pending,
    }
    result["audit_log_tail"] = audit_tail

    # Check for world-readable secrets directory
    secrets_dir = VAULT / "secrets"
    if secrets_dir.exists():
        import stat
        mode = secrets_dir.stat().st_mode
        world_readable = bool(mode & stat.S_IROTH)
        result["secrets_dir"] = {
            "exists": True,
            "path": str(secrets_dir),
            "world_readable": world_readable,
            "issue": "WARN: secrets dir is world-readable" if world_readable else None,
        }
    else:
        result["secrets_dir"] = {"exists": False}

    return result


def _human_age(seconds: float) -> str:
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m {s % 60}s"
    h = s // 3600
    m = (s % 3600) // 60
    return f"{h}h {m}m"


if __name__ == "__main__":
    data = check_security()
    print(json.dumps(data, indent=2))
