# tests/security/test_security.py
import pytest
import sqlite3
import os
from datetime import datetime, timezone
from pathlib import Path
from lib.security.context import SecurityContext, CapabilityGrant, shadow_require
from lib.security.exceptions import CapabilityDenied, TrustLevelError, CapabilityPending
from lib.security.grants import CapabilityGrantManager, CapabilityRequest
from lib.security.audit import AuditLogger
from lib.security.store import GrantStore

@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "security_audit.db"
    return db_path

@pytest.fixture
def audit_logger(temp_db):
    return AuditLogger(db_path=temp_db)

def test_require_raises_capability_denied():
    ctx = SecurityContext(agent_id="cli", trust_level=1)
    with pytest.raises(CapabilityDenied):
        ctx.require("vault:write")

def test_require_returns_valid_grant():
    ctx = SecurityContext.default("cli")
    grant = ctx.require("model:local")
    assert grant.capability == "model:local"

def test_revoke_task_grants_only_removes_task():
    ctx = SecurityContext.default("cli")
    ctx.add_grant(CapabilityGrant(
        capability="net:search", granted_at=datetime.now(timezone.utc),
        expires_at=None, granted_by="user", scope="task"
    ))
    ctx.add_grant(CapabilityGrant(
        capability="vault:read", granted_at=datetime.now(timezone.utc),
        expires_at=None, granted_by="system", scope="session"
    ))
    revoked = ctx.revoke_task_grants()
    assert revoked == 1
    assert ctx.has("vault:read")
    assert not ctx.has("net:search")

def test_clone_isolation_enforced():
    parent = SecurityContext.default("cli")
    clone = parent.child_context("clone:test")
    # Manually escalate trust level (violating isolation)
    clone.trust_level = 3 # ADMIN
    
    grant = CapabilityGrant(
        capability="vault:delete", granted_at=datetime.now(timezone.utc),
        expires_at=None, granted_by="user", scope="task"
    )
    with pytest.raises(TrustLevelError):
        clone.add_grant(grant)

def test_oob_raises_capability_pending_when_no_tty(monkeypatch, audit_logger):
    monkeypatch.setattr("lib.security.grants._has_tty", lambda: False)
    gm = CapabilityGrantManager(audit_logger=audit_logger)
    ctx = SecurityContext(agent_id="cli", trust_level=2) # ELEVATED
    with pytest.raises(CapabilityPending) as exc_info:
        gm.request(ctx, CapabilityRequest(capability="vault:write", reason="test"))
    assert exc_info.value.pending_id is not None

def test_resolve_pending_grants_capability(monkeypatch, audit_logger):
    monkeypatch.setattr("lib.security.grants._has_tty", lambda: False)
    gm = CapabilityGrantManager(audit_logger=audit_logger)
    ctx = SecurityContext(agent_id="cli", trust_level=2) # ELEVATED
    
    pending_id = None
    try:
        gm.request(ctx, CapabilityRequest(capability="vault:write", reason="test"))
    except CapabilityPending as e:
        pending_id = e.pending_id
    
    assert pending_id is not None
    grant = gm.resolve_pending(pending_id, ctx, approved=True)
    assert grant is not None
    assert ctx.has("vault:write")

def test_grant_store_persistent_restoration(audit_logger):
    ctx = SecurityContext.default("cli")
    store = GrantStore(audit_logger)
    
    grant = CapabilityGrant(
        capability="vault:read", granted_at=datetime.now(timezone.utc),
        expires_at=None, granted_by="user", scope="persistent"
    )
    audit_logger.record_granted(ctx, grant, "test persistent")
    
    # Fresh context
    ctx2 = SecurityContext.default("cli")
    assert not ctx2.has("vault:read")
    
    count = store.load_persistent_grants(ctx2)
    assert count == 1
    assert ctx2.has("vault:read")

def test_shadow_require_behavior():
    ctx = SecurityContext(agent_id="cli", trust_level=0) # UNTRUSTED
    # Should not raise, just return None
    result = shadow_require(ctx, "vault:write")
    assert result is None
