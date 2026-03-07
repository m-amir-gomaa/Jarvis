# JARVIS BOOTSTRAP — ACTIVE BUG LIST & FIX INSTRUCTIONS
**Read BOOTSTRAP_CORE.md first. This file is the session-start checklist.**
**Last updated: V3 (March 7, 2026)**

---

## 🔴 P0 — Active Production Bugs (Fix Before Anything Else)

### P0-A: `jarvis.py:99` — `messages=` kwarg passed to `ask()`

**Location:** `jarvis.py` line 99  
**Severity:** HIGH — intent classification silently fails  
**Error:** `TypeError: ask() got an unexpected keyword argument 'messages'`  
**Symptom:** `classify_intent()` returns `{"intent": "unknown"}` for all input when Ollama is available; wrapped by `except Exception` so it's silent.

**Current (broken) code:**
```python
response = ask(task="classify", privacy=Privacy.INTERNAL, messages=messages, thinking=False)
```

**Fix:**
```python
response = ask(INTENT_PROMPT + user_input, task="classify", privacy=Privacy.INTERNAL, thinking=False)
```

**Also fix:** The `match = re.search(r'\{.*\}', response, re.DOTALL)` on the next line must work on `response.content` if `ask()` returns an `LLMResponse` object rather than a plain string. Check `lib/llm.py` `ask()` return type first.

**Verify:** `jarvis 'summarize my git commits'` should classify as `git_summary` intent.

---

## 🟠 P1 — Functional Gaps

### P1-A: `/auth/conn_id` AttributeError before first LSP connection

**Location:** `services/jarvis_lsp.py` — `/auth/conn_id` endpoint  
**Severity:** MEDIUM — crashes before any Neovim window connects  
**Error:** `AttributeError: _local object has no attribute 'conn_id'`

**Current code (likely):**
```python
return {"conn_id": _thread_local.conn_id}
```

**Fix:**
```python
conn_id = getattr(_thread_local, "conn_id", None)
return {"conn_id": conn_id}
```

**Verify:** `curl http://localhost:8001/auth/conn_id` returns `{"conn_id": null}` before Neovim connects.

---

### P1-B: TUI Security / ERS / IDE tabs show static placeholder text

**Location:** `jarvis-monitor/src/ui.rs` — `render_security()`, `render_ers()`, `render_ide()`  
**Severity:** MEDIUM — feature is visually promised but not delivered

**Current code:**
```rust
fn render_security(f: &mut Frame, _app: &App, area: Rect) {
    let para = Paragraph::new("Loading from security_audit.db...")  // Never actually loads
```

**Fix approach:**
1. Add to `app.rs:App` struct:
   ```rust
   pub pending_grants: Vec<PendingGrant>,  // struct { id, ts, agent_id, capability, reason }
   pub recent_events: Vec<SecurityEvent>,  // struct { ts, agent_id, capability, action }
   ```
2. Add to `data.rs:get_security_info()` function:
   ```rust
   let db_path = vault.join("databases").join("security_audit.db");
   // PRAGMA query_only = true
   // SELECT id, ts, agent_id, capability, reason FROM pending_grants WHERE status='pending'
   // SELECT ts, agent_id, capability, action FROM capability_events ORDER BY ts DESC LIMIT 20
   ```
3. Update `render_security()` to display as a table.  
4. Run `make rust-build` after changes.

---

### P1-C: CLI has no SecurityContext — capability engine bypassed

**Location:** `jarvis.py` — intent dispatch, all pipeline calls  
**Severity:** MEDIUM for now (shadow_mode=True) — HIGH when shadow_mode disabled

This is the V1→V2 CLI migration. See `BOOTSTRAP_CLI_MIGRATION.md` for the full plan.

---

### P1-D: `lsp.lua` conn_id fetch uses blocking `vim.fn.system()`

**Location:** `lua/jarvis/ide/lsp.lua` — deferred fetch in `on_attach`  
**Severity:** LOW — blocks Neovim event loop for <1ms typically, but architecturally wrong

**Current:**
```lua
local result = vim.fn.system("curl -s http://localhost:8001/auth/conn_id")
```

**Fix:**
```lua
vim.fn.jobstart({"curl", "-s", "http://localhost:8001/auth/conn_id"}, {
  on_stdout = function(_, data)
    local s = table.concat(data)
    if s == "" then return end
    local ok, d = pcall(vim.fn.json_decode, s)
    if ok and d and d.conn_id then
      require("jarvis.ide.security").set_conn_id(d.conn_id)
    end
  end
})
```

---

## 🟡 P2 — Security Hardening

### P2-A: `resolve_pending()` doesn't re-check trust floor

**Location:** `lib/security/grants.py:CapabilityGrantManager.resolve_pending()`  
**Severity:** LOW — unlikely in practice but technically allows trust bypass

**Fix:** After `row = self.audit.get_pending(pending_id)`, add:
```python
floor = CAPABILITY_TRUST_FLOOR.get(cap, 1)
if ctx.trust_level < floor:
    self.audit.mark_pending_resolved(pending_id, "denied")
    raise TrustLevelError(f"Trust level {ctx.trust_level} insufficient for '{cap}'")
```

---

### P2-B: Monitor DB connections lack `PRAGMA query_only = true`

**Location:** `jarvis-monitor/src/data.rs`  
**Severity:** INFO — no actual risk, just defensive practice

**Fix:** When fixing P1-B (Security tab), add to each `Connection::open()`:
```rust
conn.execute("PRAGMA query_only = true", [])?;
```

---

### P2-C: `GrantStore.revoke_persistent()` uses `list.remove()` during iteration

**Location:** `lib/security/store.py:GrantStore.revoke_persistent()`  
**Severity:** LOW — works in CPython, fragile pattern

**Current:**
```python
for g in ctx.grants:
    if g.capability == capability and g.scope == "persistent":
        self.audit.record_revoked(ctx, capability, g.audit_token)
        ctx.grants.remove(g)
        return True
```

**Fix:**
```python
for g in list(ctx.grants):   # copy to avoid mutation-during-iteration
    if g.capability == capability and g.scope == "persistent":
        self.audit.record_revoked(ctx, capability, g.audit_token)
        ctx.grants = [x for x in ctx.grants if x is not g]
        return True
```

---

## 🔵 P3 — Nice to Have

### P3-A: `inline.lua` debounce not applied

**Location:** `lua/jarvis/ide/inline.lua`  
**Severity:** LOW — fires on every keystroke, generates excessive inference requests  
**Fix:** Wire `debounce_ms` option using `vim.defer_fn(callback, debounce_ms)` pattern.

### P3-B: `code_action.yaml` missing `on_failure: stop`

**Location:** `chains/clone/code_action.yaml`  
**Impact:** If `action_planner` step fails, `action_executor` gets undefined `{{ edit_plan }}` → `TemplateError`

**Fix:** Add `on_failure: stop` to `action_planner` step.

### P3-C: `chains/` YAML files missing `capabilities:` field

**Impact:** Audit trail doesn't show per-step capability requirements. Functional but incomplete.  
**Fix:** Add `capabilities: ["model:local"]` to steps that need it.

---

## ✅ Fixed in V3 (Do Not Re-Fix)

| Bug | Fixed In | Notes |
|-----|---------|-------|
| Trust ceiling always 1 (P1-5) | V3 | `authenticated` bool flag |
| DB path `data/` vs `databases/` (P1-6) | V3 | Python + Rust updated |
| conn_id not wired in lsp.lua (P1-7) | V3 | Deferred fetch added |
| OpenAI adapter model arg positional | V3 | Signature fixed |
| ERS stale comment | V3 | Removed |
| `test_router/llm/react` stale signatures | V3 | Tests updated |
| BUG-1 `eval()` in trigger | V2.1 | `simpleeval` |
| BUG-2 `scope` column missing | V2.1 | Added to schema |
| BUG-3 Shared mutable context in batch | V2.1 | `child_context` per step |
| BUG-4 `shadow_require` only caught one exception | V2.1 | Both caught |
| GAP-5 Session token spec | V2.1 | Fully implemented |
| GAP-6 Lua poll loop (60 curl processes) | V2.1 | Long-poll with guard |
| GAP-7 requirements-v2.txt missing | V2.1 | Created |
| GAP-8 ChainLoader no load-time validation | V2.1 | `_validate()` added |

---

## Fix Priority Order for Next Session

```
1. P0-A  jarvis.py:99 messages= kwarg         (5 min fix, breaks daily use)
2. P1-A  /auth/conn_id AttributeError          (2 min fix, affects LSP startup)
3. P1-D  lsp.lua blocking system() call        (5 min fix, clean pattern)
4. P2-C  GrantStore.revoke_persistent()        (3 min fix, correctness)
5. P2-A  resolve_pending trust floor check     (5 min fix, security)
6. P1-B  TUI Security tab live data            (2 hour feature, high visibility)
7. P3-A  inline.lua debounce                  (30 min)
8. P3-B  code_action.yaml on_failure          (2 min)
9. P1-C  CLI V1→V2 migration                  (multi-session major work)
```
