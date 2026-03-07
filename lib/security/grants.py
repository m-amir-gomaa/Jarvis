# lib/security/grants.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Literal
import os, sys, uuid

from .context import CapabilityGrant, SecurityContext, CAPABILITY_TRUST_FLOOR, TRUST_LEVELS
from .exceptions import CapabilityDenied, TrustLevelError, CapabilityPending


@dataclass
class CapabilityRequest:
    capability:   str
    reason:       str
    scope:        Literal["task", "session", "persistent"] = "task"
    cost_hint:    str | None = None
    provider:     str | None = None


def _has_tty() -> bool:
    """Returns True if a real interactive TTY is available."""
    return sys.stdin.isatty() and sys.stdout.isatty()


class CapabilityGrantManager:
    def __init__(
        self,
        audit_logger,
        interactive_prompt: Callable[[str], bool] = None,
        auto_grant_local_model: bool = True,
        auto_grant_ide_read: bool   = True,
        prompt_style: Literal["interactive", "auto_deny", "auto_allow", "oob"] = "interactive",
    ):
        self.audit          = audit_logger
        self._prompt        = interactive_prompt or self._default_prompt
        self.auto_grants    = set()
        self.prompt_style   = prompt_style
        if auto_grant_local_model:
            self.auto_grants.add("model:local")
        if auto_grant_ide_read:
            self.auto_grants.add("ide:read")

    @staticmethod
    def _default_prompt(message: str) -> bool:
        resp = input(f"\n[JARVIS PERMISSION] {message} [y/N] ").strip().lower()
        return resp in ("y", "yes")

    def _effective_style(self) -> str:
        """Auto-detect OOB mode when no TTY is available."""
        if self.prompt_style == "interactive" and not _has_tty():
            return "oob"
        return self.prompt_style

    def request(
        self,
        ctx: SecurityContext,
        req: CapabilityRequest,
    ) -> CapabilityGrant:
        cap   = req.capability
        floor = CAPABILITY_TRUST_FLOOR.get(cap, 1)

        # Trust level check
        if ctx.trust_level < floor:
            self.audit.record_denied(ctx, cap, req.reason, "trust_level_insufficient", scope=req.scope)
            raise TrustLevelError(
                f"TrustLevel {ctx.trust_level} insufficient for '{cap}' (requires {floor})"
            )

        # Auto-grant check
        if cap in self.auto_grants:
            grant = self._issue(ctx, cap, req, granted_by="system")
            self.audit.record_granted(ctx, grant, req.reason, auto=True)
            ctx.add_grant(grant)
            return grant

        # Already held?
        if ctx.has(cap):
            return ctx.require(cap)

        style = self._effective_style()

        if style == "auto_deny":
            self.audit.record_denied(ctx, cap, req.reason, "auto_deny_policy", scope=req.scope)
            raise CapabilityDenied(cap, ctx.agent_id)

        if style == "auto_allow":
            grant = self._issue(ctx, cap, req, granted_by="system")
            self.audit.record_granted(ctx, grant, req.reason, auto=True)
            ctx.add_grant(grant)
            return grant

        if style == "oob":
            # No TTY — write pending record and raise CapabilityPending
            pending_id = str(uuid.uuid4())[:8]
            self.audit.record_pending(ctx, cap, req.reason, pending_id)
            raise CapabilityPending(cap, ctx.agent_id, pending_id)

        # style == "interactive" — blocking TTY prompt
        msg = self._build_message(cap, req)
        if self._prompt(msg):
            grant = self._issue(ctx, cap, req, granted_by="user")
            self.audit.record_granted(ctx, grant, req.reason, auto=False)
            ctx.add_grant(grant)
            return grant
        else:
            self.audit.record_denied(ctx, cap, req.reason, "user_denied", scope=req.scope)
            raise CapabilityDenied(cap, ctx.agent_id)

    def resolve_pending(self, pending_id: str, ctx: SecurityContext, approved: bool) -> CapabilityGrant | None:
        """
        Resolve an OOB pending grant. Called by 'jarvis approve <id>' or jarvis-lsp.
        Returns the issued grant if approved, None if denied.
        """
        row = self.audit.get_pending(pending_id)
        if row is None:
            raise ValueError(f"No pending grant found with id: {pending_id}")
        cap = row["capability"]
        req = CapabilityRequest(capability=cap, reason=row["reason"], scope=row.get("scope", "task"))
        if approved:
            # Re-check trust floor before issuing — prevents trust bypass via OOB
            floor = CAPABILITY_TRUST_FLOOR.get(cap, 1)
            if ctx.trust_level < floor:
                self.audit.record_denied(ctx, cap, req.reason, "trust_level_insufficient_at_resolve", scope=req.scope)
                self.audit.mark_pending_resolved(pending_id, "denied")
                raise TrustLevelError(
                    f"Trust level {ctx.trust_level} insufficient for '{cap}' (requires {floor})"
                )
            grant = self._issue(ctx, cap, req, granted_by="user")
            self.audit.record_granted(ctx, grant, req.reason, auto=False)
            self.audit.mark_pending_resolved(pending_id, "approved")
            ctx.add_grant(grant)
            return grant
        else:
            self.audit.record_denied(ctx, cap, req.reason, "user_denied_oob", scope=req.scope)
            self.audit.mark_pending_resolved(pending_id, "denied")
            return None

    def _build_message(self, cap: str, req: CapabilityRequest) -> str:
        base = f"Jarvis wants '{cap}' for: {req.reason}"
        if req.cost_hint:
            base += f"  [Est. cost: {req.cost_hint}]"
        if req.provider:
            base += f"  [Provider: {req.provider}]"
        base += f"  [Scope: {req.scope}]"
        return base

    def _issue(self, ctx: SecurityContext, cap: str, req: CapabilityRequest, granted_by: str = "user") -> CapabilityGrant:
        return CapabilityGrant(
            capability=cap,
            granted_at=datetime.now(timezone.utc),
            expires_at=None,
            granted_by=granted_by,
            scope=req.scope,
            audit_token=str(uuid.uuid4()),
        )
