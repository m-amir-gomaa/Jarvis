# lib/security/audit.py
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .context import SecurityContext, CapabilityGrant

DB_PATH = Path("/THE_VAULT/jarvis/databases/security_audit.db")

class AuditLogger:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS capability_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT DEFAULT CURRENT_TIMESTAMP,
                    agent_id TEXT,
                    capability TEXT,
                    action TEXT,
                    reason TEXT,
                    granted_by TEXT,
                    audit_token TEXT,
                    auto INTEGER,
                    denial_reason TEXT,
                    scope TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pending_grants (
                    id TEXT PRIMARY KEY,
                    ts TEXT DEFAULT CURRENT_TIMESTAMP,
                    agent_id TEXT,
                    capability TEXT,
                    reason TEXT,
                    scope TEXT,
                    status TEXT DEFAULT 'pending'
                )
            """)
            conn.commit()

    def record_granted(self, ctx: SecurityContext, grant: CapabilityGrant, reason: str, auto: bool = False):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO capability_events 
                (agent_id, capability, action, reason, granted_by, audit_token, auto, scope)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (ctx.agent_id, grant.capability, 'granted', reason, grant.granted_by, grant.audit_token, 1 if auto else 0, grant.scope))
            conn.commit()

    def record_denied(self, ctx: SecurityContext, capability: str, reason: str, denial_reason: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO capability_events 
                (agent_id, capability, action, reason, denial_reason)
                VALUES (?, ?, ?, ?, ?)
            """, (ctx.agent_id, capability, 'denied', reason, denial_reason))
            conn.commit()

    def record_pending(self, ctx: SecurityContext, capability: str, reason: str, pending_id: str, scope: str = "task"):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO pending_grants 
                (id, agent_id, capability, reason, scope)
                VALUES (?, ?, ?, ?, ?)
            """, (pending_id, ctx.agent_id, capability, reason, scope))
            conn.commit()

    def record_revoked(self, ctx: SecurityContext, capability: str, audit_token: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO capability_events 
                (agent_id, capability, action, audit_token)
                VALUES (?, ?, ?, ?)
            """, (ctx.agent_id, capability, 'revoked', audit_token))
            conn.commit()

    def get_pending(self, pending_id: str) -> dict[str, Any] | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM pending_grants WHERE id=? AND status='pending'", (pending_id,)
            ).fetchone()
        return dict(row) if row else None

    def list_pending(self) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM pending_grants WHERE status='pending' ORDER BY ts DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def mark_pending_resolved(self, pending_id: str, status: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE pending_grants SET status=? WHERE id=?", (status, pending_id))
            conn.commit()
