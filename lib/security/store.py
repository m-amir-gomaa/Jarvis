# lib/security/store.py
from __future__ import annotations
import sqlite3
from datetime import datetime
from .context import SecurityContext, CapabilityGrant

class GrantStore:
    def __init__(self, audit_logger):
        self.audit = audit_logger

    def load_persistent_grants(self, ctx: SecurityContext) -> int:
        """
        Load all persistent grants for this agent_id from the DB into the context.
        """
        restored = 0
        with sqlite3.connect(self.audit.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT ce.*
                FROM capability_events ce
                WHERE ce.agent_id = ?
                  AND ce.action   = 'granted'
                  AND ce.scope    = 'persistent'
                  AND ce.audit_token NOT IN (
                      SELECT audit_token
                      FROM capability_events
                      WHERE action = 'revoked'
                        AND audit_token IS NOT NULL
                  )
                ORDER BY ce.ts ASC
                """,
                (ctx.agent_id,)
            ).fetchall()
        for row in rows:
            grant = CapabilityGrant(
                capability=row["capability"],
                granted_at=datetime.fromisoformat(row["ts"]),
                expires_at=None,
                granted_by=row["granted_by"] or "persistent",
                scope="persistent",
                audit_token=row["audit_token"],
            )
            if not ctx.has(grant.capability):
                ctx.add_grant(grant)
                restored += 1
        return restored

    def revoke_persistent(self, ctx: SecurityContext, capability: str) -> bool:
        """Explicitly revoke a persistent grant."""
        for g in list(ctx.grants):  # copy to avoid mutation during iteration
            if g.capability == capability and g.scope == "persistent":
                self.audit.record_revoked(ctx, capability, g.audit_token)
                ctx.grants = [x for x in ctx.grants if x is not g]
                return True
        return False
