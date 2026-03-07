# JARVIS BOOTSTRAP — SECURITY ENGINE
**Read BOOTSTRAP_CORE.md first.**

---

## Files

```
lib/security/
  __init__.py         # Exports: SecurityContext, TrustLevel, CapabilityGrant, shadow_require
  context.py          # Core types: TrustLevel, CapabilityGrant, SecurityContext, shadow_require
  grants.py           # CapabilityGrantManager — policy enforcement
  store.py            # GrantStore — persistent grant serialization
  audit.py            # AuditLogger — writes events to security_audit.db
  exceptions.py       # CapabilityDenied, TrustLevelError, CapabilityExpired, CapabilityPending
  secrets.py          # AES-256 keyring for API keys
```

---

## Trust Levels

```python
TRUST_LEVELS = {
    "UNTRUSTED": 0,  # No permissions
    "BASIC":     1,  # Local model, chat, ide:read
    "ELEVATED":  2,  # IDE edits, search, external models
    "ADMIN":     3,  # File exec, vcs:write
    "SYSTEM":    4,  # Daemon-level, system:daemon only
}
```

---

## Capability Floor Map (CAPABILITY_TRUST_FLOOR)

```python
{
    "chat:basic":         1,  "chat:multimodel":     2,
    "ide:read":           1,  "ide:edit":            2,
    "fs:validate":        1,  "fs:exec":             3,
    "vault:read":         1,  "vault:write":         2,  "vault:delete": 3,
    "net:search":         2,  "net:external":        3,
    "model:local":        1,  "model:external":      2,
    "debug:read":         1,  "debug:exec":          2,
    "vcs:read":           1,  "vcs:write":           3,
    "security:grant":     3,  "security:audit":      2,
    "reasoning:elevated": 2,  "system:daemon":       4,
}
```

---

## SecurityContext API

```python
ctx = SecurityContext(agent_id="cli", trust_level=3)

# Check
ctx.has("ide:edit")            # bool — has valid unexpired grant?
ctx.require("ide:edit")        # CapabilityGrant or raises CapabilityDenied/Expired
ctx.add_grant(grant)           # Add; enforces clone ceiling
ctx.revoke_task_grants()       # Returns count revoked — called in ERS finally blocks
ctx.child_context("name", trust_ceiling=2)  # Clone with ceiling

# Factory
SecurityContext.default("agent_id")  # BASIC + model:local + chat:basic auto-granted
```

**Clone isolation rule:** `child_context.trust_level = min(parent.trust_level, trust_ceiling)`. Clone cannot escalate beyond parent. Enforced in `add_grant()`.

---

## CapabilityGrantManager

```python
mgr = CapabilityGrantManager(
    audit_logger=audit,
    auto_grant_local_model=True,   # "model:local" never prompts
    auto_grant_ide_read=True,      # "ide:read" never prompts
    prompt_style="interactive",    # or "auto_deny" | "auto_allow" | "oob"
)

grant = mgr.request(ctx, CapabilityRequest(
    capability="ide:edit",
    reason="Fix code at cursor",
    scope="task",          # "task" | "session" | "persistent"
))
```

**Style precedence:**
1. If `prompt_style="interactive"` AND no TTY → auto-switches to `"oob"`
2. OOB mode: writes to `pending_grants` table, raises `CapabilityPending(cap, agent_id, pending_id)`
3. `resolve_pending(pending_id, ctx, approved=True)` — called by `jarvis approve <id>`

---

## AuditLogger (security_audit.db)

```sql
-- Table 1: All events
capability_events(id, ts, agent_id, capability, action, scope, reason, granted_by, audit_token, auto, denial_reason)
-- action: 'granted' | 'denied' | 'revoked' | 'pending'

-- Table 2: Pending OOB requests
pending_grants(id, ts, agent_id, capability, reason, scope, status)
-- status: 'pending' | 'approved' | 'denied'
```

DB path: `/THE_VAULT/jarvis/databases/security_audit.db`
Indices (added V3): `idx_events_agent_ts(agent_id, ts)`, `idx_pending_status_ts(status, ts)`

---

## GrantStore (Persistent Grants)

```python
store = GrantStore(audit_logger)
store.load_persistent_grants(ctx)   # Restores from DB into ctx.grants at startup
store.revoke_persistent(ctx, "model:external")  # Marks revoked in audit log
```

Persistent grants survive process restarts. Use `scope="persistent"` in `CapabilityRequest`.

---

## OOB Approval Flow (Full)

```
Non-interactive context (daemon, LSP):
  1. mgr.request() → detects no TTY → writes pending_grants row
  2. raises CapabilityPending(cap, agent_id, pending_id)
  3. Caller (LSP route) catches CapabilityPending → returns HTTP {"error":"pending","pending_id":"..."}
  4. Lua security.lua receives pending_id → starts _poll_pending(pending_id)
  5. Lua polls GET /security/pending?timeout=10&conn_id=<conn_id>
  6. User runs: jarvis pending  (lists all pending_grants)
  7. User runs: jarvis approve <pending_id>
  8. jarvis.py calls mgr.resolve_pending(pending_id, ctx, approved=True)
  9. Long-poll at step 4 receives the resolution → callback(granted=true)
 10. Lua calls the original action callback → proceeds with the IDE action
```

---

## shadow_require

```python
# During Phase 1 rollout — denials are LOGGED but NOT enforced
from lib.security.context import shadow_require, SecurityContext
shadow_require(ctx, "ide:edit")  # Returns None instead of raising
```

`shadow_mode=True` is still the default. Do NOT change this until explicit decision.

---

## Secrets (API Keys)

```python
from lib.security.secrets import SecretsManager
sm = SecretsManager()
key = sm.get("ANTHROPIC_API_KEY")   # Returns None if not set
sm.set("ANTHROPIC_API_KEY", "sk-...")  # AES-256 encrypt + store in .keyring
```

Keyring file: `/THE_VAULT/jarvis/secrets/.keyring` (must be created by user, not auto-created)

---

## Known Issues (see BOOTSTRAP_BUGS.md for full detail)

- `resolve_pending()` does not re-check trust floor before issuing — minor security gap
- `GrantStore.revoke_persistent()` uses `list.remove()` instead of list comprehension — fragile but works in CPython
- `SecurityContext.grants` list is not thread-safe for concurrent writes (mitigated by child_context per ERS step)
