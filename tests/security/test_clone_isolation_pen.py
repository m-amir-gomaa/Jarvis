# tests/security/test_clone_isolation_pen.py
import pytest
from lib.security.context import SecurityContext, CapabilityGrant
from lib.security.exceptions import TrustLevelError, CapabilityDenied
from datetime import datetime, timezone

def test_clone_cannot_escalate_trust_level():
    # Parent is BASIC (1)
    parent = SecurityContext.default("parent")
    parent.trust_level = 1
    
    # Attempt to create a child with ELEVATED (2) ceiling - should fail or be capped
    # Our implementation currently allows specifying ceiling, but it must be <= parent level
    # or it will be capped at parent's level in child_context()
    child = parent.child_context("child", trust_ceiling=3) 
    
    # Check if the ceiling was capped
    assert child.trust_level <= parent.trust_level
    
def test_clone_cannot_issue_grant_to_self():
    parent = SecurityContext.default("parent")
    parent.trust_level = 2 # ELEVATED
    
    child = parent.child_context("child", trust_ceiling=2)
    
    # Child attempts to add a grant to itself directly via add_grant
    # add_grant doesn't check permissions (it's a low-level state mutation)
    # But in a real scenario, the child doesn't have access to its own context object
    # across a process or bridge boundary.
    # The real test is: can it call gm.request for a cap above its level?
    from lib.security.grants import CapabilityGrantManager, CapabilityRequest
    from unittest.mock import MagicMock
    
    gm = CapabilityGrantManager(audit_logger=MagicMock())
    
    # Requesting ADMIN cap from ELEVATED context
    with pytest.raises(TrustLevelError):
        gm.request(child, CapabilityRequest(
            capability="vcs:write", # Requires ADMIN (3)
            reason="hack",
            scope="task"
        ))

def test_clone_isolation_token_leak_prevention():
    # Verify that child context grants do not propagate to parent
    parent = SecurityContext.default("parent")
    child = parent.child_context("child")
    
    grant = CapabilityGrant(
        capability="test:cap",
        granted_at=datetime.now(timezone.utc),
        expires_at=None,
        granted_by="test",
        scope="task"
    )
    
    child.add_grant(grant)
    assert child.has("test:cap")
    assert not parent.has("test:cap")
