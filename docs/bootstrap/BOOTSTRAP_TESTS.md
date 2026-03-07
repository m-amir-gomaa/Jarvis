# JARVIS BOOTSTRAP — TEST SUITE REFERENCE
**Read BOOTSTRAP_CORE.md first.**

---

## Running Tests

```bash
cd ~/NixOSenv/Jarvis
source /THE_VAULT/jarvis/.venv/bin/activate

make test-all       # Full suite (all phases + unit tests)
make test-security  # Phase 1: Security engine
make test-ers       # Phase 2: ERS chain execution
make test-router    # Model router V1 routing
make test-llm       # V1 LLM bridge
make test-react     # ReAct agent loop parser
make test-budget    # Budget controller
make test-cloud     # Cloud adapter key detection
make test-memory    # Episodic/semantic memory
make test-tools     # Tool dispatch
```

---

## Test Suite Map

### Phase Gate Tests (run as part of `make test-all`)

| Make Target | File | Tests | Status |
|------------|------|-------|--------|
| `test-security` | `tests/test_stage_1_remediation.py` | Grant adding, clone trust ceil, shadow mode | ✅ |
| `test-ers` | `tests/ers/test_ers.py` | Chain execution, on_failure, batch | ✅ |
| `test-chain-loader` | `tests/ers/test_chain_loader.py` | YAML validation, ChainValidationError | ✅ |
| `test-llm-bridge` | `tests/test_llm_bridge.py` | V1/V2 llm compatibility | ✅ |

### Unit / Tool Tests

| Make Target | File | What It Tests |
|------------|------|--------------|
| `test-budget` | `tools/test_budget.py` | `lib/budget_controller.py` DB r/w |
| `test-budget-session` | `tools/test_budget_session.py` | Per-session budget isolation |
| `test-router` | `tools/test_router.py` | `lib/model_router.route()` Privacy routing |
| `test-cloud` | `tools/test_cloud.py` | Cloud adapter API key detection |
| `test-llm` | `tools/test_llm.py` | `lib/llm.ask()` with local Ollama |
| `test-memory` | `tools/test_memory.py` | Episodic + semantic memory ops |
| `test-tools` | `tools/test_tools.py` | Tool dispatch (`lib/tools.py`) |
| `test-react` | `tools/test_react.py` | `AgentLoop._get_next_action()` parser |

---

## Test Signatures (CRITICAL — match these exactly after V3 fixes)

### `ask()` in `lib/llm.py`
```python
def ask(
    prompt: str,          # POSITIONAL — first arg
    *,                    # Everything else is keyword-only
    task: str = "general",
    model: str | None = None,
    privacy: Privacy = Privacy.PRIVATE,
    ctx = None,           # SecurityContext | None
    max_tokens: int = 2048,
    system: str | None = None,
    thinking: bool = False,
) -> LLMResponse:
```

**DO NOT pass `messages=` to `ask()`** — it doesn't accept that kwarg.

### `route()` in `lib/model_router.py`
```python
def route(
    *,                    # ALL keyword-only
    prompt: str,
    privacy: Privacy,
    ctx = None,
    task_type: str = "general",
) -> RouteDecision:
```

**DO NOT pass positional args to `route()`** — it's keyword-only.

### `AgentLoop._get_next_action()`
```python
def _get_next_action(self, history: list[dict], user_prompt: str, response: Any) -> AgentAction:
```

**Three required args** — `response` is the pre-fetched LLM reply (not fetched inside the method).

---

## Coverage Gaps (Not Yet Tested)

| Component | What's Missing |
|----------|---------------|
| `services/jarvis_lsp.py` | No pytest tests for IDE routes |
| `lua/jarvis/ide/` | No automated Lua tests |
| `jarvis-monitor/` | No Rust tests (compile-only) |
| `lib/security/audit.py` | Concurrent write behavior |
| `lib/security/grants.py` | OOB flow end-to-end |
| `lib/ers/augmentor.py` | Batch RAM gate behavior |
| `chains/*.yaml` | No execution tests with real Ollama |
| `jarvis.py` classify_intent() | No test for intent routing |

---

## Adding New Tests

### For Python (pytest style):

```python
# tests/test_my_component.py
import pytest
from lib.security.context import SecurityContext

def test_something():
    ctx = SecurityContext.default("test-agent")
    assert ctx.has("model:local")

# Run: python -m pytest tests/test_my_component.py -v
# Or add target to Makefile
```

### For ERS chains (real inference required):

```python
import asyncio
from lib.ers.chain import ChainLoader
from lib.ers.augmentor import ChainAugmentor
# Requires: Ollama running with the model specified in chain

async def test_chain():
    loader = ChainLoader()
    chain = loader.load_file("chains/git_summarize.yaml")
    augmentor = ChainAugmentor(model_router, security_manager)
    result = await augmentor.run_chain(chain, ctx, {"diff": "..."})
    assert result.success
```

---

## Makefile Test Target Pattern

```makefile
test-mynewtest:
	$(VENV_PY) tools/test_mynewtest.py
```

Add to `test-all` dependency chain:
```makefile
test-all: test-mvp1 test-mvp2 test-mvp3 test-security test-ers test-router test-llm test-react test-mynewtest
```
