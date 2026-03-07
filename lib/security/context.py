# lib/security/context.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal
import uuid

TrustLevelName = Literal["UNTRUSTED", "BASIC", "ELEVATED", "ADMIN", "SYSTEM"]

TRUST_LEVELS: dict[TrustLevelName, int] = {
    "UNTRUSTED": 0,
    "BASIC":     1,
    "ELEVATED":  2,
    "ADMIN":     3,
    "SYSTEM":    4,
}

# Minimum trust level required to hold each capability
CAPABILITY_TRUST_FLOOR: dict[str, int] = {
    "chat:basic":          1,
    "chat:multimodel":     2,
    "ide:read":            1,
    "ide:edit":            2,
    "fs:validate":         1,
    "fs:exec":             3,
    "vault:read":          1,
    "vault:write":         2,
    "vault:delete":        3,
    "net:search":          2,
    "net:external":        3,
    "model:local":         1,
    "model:external":      2,
    "debug:read":          1,
    "debug:exec":          2,
    "vcs:read":            1,
    "vcs:write":           3,
    "security:grant":      3,
    "security:audit":      2,
    "reasoning:elevated":  2,
    "system:daemon":       4,
}

@dataclass
class CapabilityGrant:
    capability:   str
    granted_at:   datetime
    expires_at:   datetime | None   # None = session-scoped
    granted_by:   str               # 'user' | 'system' | 'ers:<chain_id>'
    scope:        Literal["task", "session", "persistent"]
    audit_token:  str = field(default_factory=lambda: str(uuid.uuid4()))

    def is_valid(self) -> bool:
        if self.expires_at is None:
            return True
        return datetime.now(timezone.utc) < self.expires_at


@dataclass
class SecurityContext:
    agent_id:    str
    trust_level: int                  # numeric TrustLevel (0–4)
    grants:      list[CapabilityGrant] = field(default_factory=list)
    parent_ctx:  SecurityContext | None = field(default=None, repr=False)
    is_clone:    bool = False # FIX-CONTEXT-1

    def has(self, cap: str) -> bool:
        return any(g.capability == cap and g.is_valid() for g in self.grants)

    def require(self, cap: str) -> CapabilityGrant:
        from .exceptions import CapabilityDenied, CapabilityExpired
        for g in self.grants:
            if g.capability == cap:
                if g.is_valid():
                    return g
                raise CapabilityExpired(cap, self.agent_id)
        raise CapabilityDenied(cap, self.agent_id)

    def add_grant(self, grant: CapabilityGrant) -> None:
        if self.is_clone:
            from .exceptions import TrustLevelError
            assert self.parent_ctx is not None, "Clone must have a parent context"
            if self.trust_level > self.parent_ctx.trust_level:
                raise TrustLevelError(
                    f"Clone trust_level {self.trust_level} exceeds "
                    f"parent {self.parent_ctx.trust_level}"
                )
        self.grants.append(grant)

    def revoke_task_grants(self) -> int:
        """Revoke all task-scoped grants. Returns count revoked."""
        before = len(self.grants)
        self.grants = [g for g in self.grants if g.scope != "task"]
        return before - len(self.grants)

    def child_context(self, agent_id: str, trust_ceiling: int | None = None) -> SecurityContext:
        """Create a child SecurityContext (for clone isolation)."""
        child_trust = min(self.trust_level, trust_ceiling or self.trust_level)
        return SecurityContext(
            agent_id=agent_id,
            trust_level=child_trust,
            grants=[],
            parent_ctx=self,
            is_clone=True,
        )

    @classmethod
    def default(cls, agent_id: str = "cli") -> SecurityContext:
        """Create a BASIC trust-level context with model:local auto-granted."""
        ctx = cls(agent_id=agent_id, trust_level=TRUST_LEVELS["BASIC"])
        ctx.add_grant(CapabilityGrant(
            capability="model:local",
            granted_at=datetime.now(timezone.utc),
            expires_at=None,
            granted_by="system",
            scope="session",
        ))
        ctx.add_grant(CapabilityGrant(
            capability="chat:basic",
            granted_at=datetime.now(timezone.utc),
            expires_at=None,
            granted_by="system",
            scope="session",
        ))
        return ctx

def shadow_require(ctx: SecurityContext, cap: str):
    """
    Shadow mode wrapper: log denied/trust-error but continue execution.
    """
    from .exceptions import TrustLevelError, CapabilityDenied
    try:
        return ctx.require(cap)
    except (CapabilityDenied, TrustLevelError) as e:
        import logging
        logging.getLogger("jarvis.security").warning(
            f"[SHADOW MODE] Security check failed (would block in enforcement mode): "
            f"{type(e).__name__}: {e}"
        )
        return None   # Caller continues without grant
