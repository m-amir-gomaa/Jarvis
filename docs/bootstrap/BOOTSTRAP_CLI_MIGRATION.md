# JARVIS BOOTSTRAP — CLI V1→V2 MIGRATION PLAN
**Read BOOTSTRAP_CORE.md and BOOTSTRAP_SECURITY.md first.**
**This is the major remaining architectural work.**

---

## The Problem

`jarvis.py` (the main CLI) was built in the V1 era. It uses:
- `lib/llm.py` (V1 ask() wrapper)
- `lib/model_router.py` (V1 Privacy enum routing)
- `lib/ollama_client.py` (direct Ollama calls)

It does **NOT** use:
- `lib/security/` capability engine
- `lib/models/` adapter hub
- `lib/ers/` chain system

This means:
1. All CLI-triggered pipelines run without a SecurityContext.
2. The capability audit trail is completely absent for CLI usage.
3. When `shadow_mode` is disabled, the system will be inconsistent.
4. Users can't `jarvis approve` for CLI-triggered pipelines waiting on capabilities.

---

## Migration Strategy

### Phase A: CLI SecurityContext Bootstrap (Non-Breaking)

**Effort:** ~2 hours  
**Risk:** Low (shadow_mode stays True)

1. At startup, create a CLI SecurityContext with ADMIN trust:
```python
# jarvis.py — add near top, after _ensure_session_token()

from lib.security.context import SecurityContext, TRUST_LEVELS
from lib.security.grants import CapabilityGrantManager
from lib.security.audit import AuditLogger
from lib.security.store import GrantStore

_VAULT_ROOT = Path(os.environ.get("VAULT_ROOT", "/THE_VAULT/jarvis"))
_audit = AuditLogger(_VAULT_ROOT / "databases" / "security_audit.db")
_grant_mgr = CapabilityGrantManager(
    audit_logger=_audit,
    auto_grant_local_model=True,
    auto_grant_ide_read=True,
    prompt_style="interactive",
)

def _create_cli_ctx() -> SecurityContext:
    ctx = SecurityContext(agent_id="cli", trust_level=TRUST_LEVELS["ADMIN"])
    # Restore persistent grants from previous sessions
    store = GrantStore(_audit)
    restored = store.load_persistent_grants(ctx)
    if restored:
        print(f"[Jarvis] Restored {restored} persistent capability grant(s)")
    return ctx

CLI_CTX: SecurityContext = _create_cli_ctx()
```

2. Pass `CLI_CTX` to all pipeline dispatches (step B).

---

### Phase B: Thread-throughs to Pipelines (Non-Breaking)

**Effort:** ~3 hours  
**Risk:** Low

For each pipeline called from `jarvis.py`, pass the ctx:

```python
# Current:
run_pipeline([VENV_PY, "pipelines/research_agent.py", "--query", args.query])

# Migrated:
from lib.llm import ask, Privacy
from lib.security.context import shadow_require

shadow_require(CLI_CTX, "net:search")  # logged but not enforced in shadow_mode
result = ask(
    args.query,
    task="research",
    privacy=Privacy.PUBLIC,
    ctx=CLI_CTX,
)
```

This is the **hardest part** — most pipelines are launched as subprocess calls. Options:
1. **Direct Python import**: replace subprocess with direct function calls (preferred)
2. **Env var ctx serialization**: serialize ctx grants to env var (hacky, avoid)
3. **Hybrid**: subprocess for complex pipelines, direct calls for simple ones

---

### Phase C: Intent Classification Fix (P0-A) + V2 Router

**Effort:** 30 minutes  
**Risk:** Low

Fix `classify_intent()` to use the correct `ask()` signature:

```python
def classify_intent(user_input: str) -> dict:
    try:
        from lib.ollama_client import is_healthy
        from lib.llm import ask, Privacy
        if not is_healthy():
            return {"intent": "unknown", "args": {}}

        response = ask(
            INTENT_PROMPT + user_input,
            task="classify",
            privacy=Privacy.INTERNAL,
            thinking=False,
        )
        # ask() returns LLMResponse — get .content
        text = response.content if hasattr(response, "content") else str(response)
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception as e:
        print(f"[Jarvis] Intent classification failed: {e}", file=sys.stderr)
    return {"intent": "unknown", "args": {}}
```

---

### Phase D: Replace V1 Pipeline Dispatches with ERS Chains

**Effort:** Per pipeline, ~1 hour each  
**Risk:** Medium — behavior changes

Map of V1 subprocess pipelines → ERS equivalents:

| V1 Subprocess | V2 ERS Chain | Status |
|--------------|-------------|--------|
| `pipelines/research_agent.py` | `chains/research_deep.yaml` | ⬜ Not yet |
| `pipelines/git_summarizer.py` | `chains/git_summarize.yaml` | ⬜ Not yet |
| `pipelines/nixos_validator.py` | `chains/nixos_verify.yaml` | ⬜ Not yet |
| `pipelines/refactor_agent.py` | (TODO: create chain) | ⬜ Not yet |
| `pipelines/agent_loop.py` | (V1 stays — complex) | 🔵 Keep V1 |
| `pipelines/doc_learner.py` | (V1 stays — I/O heavy) | 🔵 Keep V1 |

For each migration:
1. Load chain from `ChainLoader`
2. Call `augmentor.run_chain(chain, CLI_CTX, initial_context)`
3. Display `result.outputs["<final_output_key>"]`
4. Remove subprocess dispatch

---

### Phase E: Disable Shadow Mode (Final Gate)

**Effort:** 5 minutes  
**Risk:** HIGH — all ungated capability requests will fail

Prerequisites:
- All pipelines have been migrated to V2 context (Phase D complete)
- All pipeline capability requirements verified in testing
- `jarvis approve` flow tested end-to-end

Switch:
```python
# In jarvis.py _create_cli_ctx():
_grant_mgr = CapabilityGrantManager(
    ...
    prompt_style="interactive",  # stays
)
# Remove shadow_require calls, replace with require()
```

---

## Testing CLI Migration

After each phase:

```bash
# Phase A test:
jarvis status         # Should print "Restored N persistent grants" if any

# Phase B/C test:
jarvis 'summarize my git commits'   # Should classify as git_summary, not unknown

# Phase D test (after each pipeline):
jarvis 'search for NixOS flake patterns'   # End-to-end via ERS
```

---

## Key Files to Modify

| File | Change |
|------|--------|
| `jarvis.py` | Add CLI_CTX creation, fix classify_intent(), thread ctx to dispatches |
| `lib/llm.py` | Ensure `ask()` propagates ctx to model_router |
| `lib/model_router.py` | Route decisions respect ctx.has("model:external") |
| Per pipeline | Accept ctx parameter or refactor to direct function call |
