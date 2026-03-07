# JARVIS BOOTSTRAP — EXTERNAL REASONING SYSTEM (ERS)
**Read BOOTSTRAP_CORE.md first.**

---

## Files

```
lib/ers/
  __init__.py
  schema.py           # Pydantic models: ReasoningChain, ReasoningStep
  chain.py            # ChainLoader + ChainValidationError
  augmentor.py        # ChainAugmentor — executes chains
  seed_loader.py      # PromptSeedLoader — wraps existing prompts
  access_protocol.py  # ERSAccessProtocol — per-step capability requests

chains/               # YAML chain definitions (scanned recursively)
  research_deep.yaml
  research_and_summarize.yaml
  debug_error.yaml
  git_summarize.yaml
  nixos_verify.yaml
  security_audit.yaml
  clone/
    code_action.yaml   # IDE fix/refactor
    code_review.yaml   # Parallel syntax+logic+security review
```

---

## ReasoningStep Schema (Pydantic)

```python
class ReasoningStep(BaseModel):
    id:              str           # Unique within chain
    prompt_template: str           # Jinja2 template
    model_alias:     str           # "reason"|"coder"|"fast"|"chat" or full spec
    output_key:      str | None    # Key written to execution_context
    batch_group:     str | None    # Steps with same batch_group run in parallel
    on_failure:      str = "continue"  # "continue" | "stop"
    stop_sequences:  list[str] = []
    max_tokens:      int = 1024
    capabilities:    list[str] = []   # Required capabilities (informational)
```

## ReasoningChain Schema

```python
class ReasoningChain(BaseModel):
    id:          str
    description: str
    steps:       list[ReasoningStep]
    seed_prompt: str | None = None  # Optional seed wrapping
```

---

## ChainLoader

```python
loader = ChainLoader()  # Defaults to JARVIS_ROOT/chains/
chains = loader.load_all()           # Returns {chain_id: ReasoningChain}
chain = loader.load_file("path.yaml")  # Single file
chain = loader.get("clone_code_review")  # From registry
```

**Validation order (fail-fast):**
1. YAML parse error → `ChainValidationError`
2. Missing required fields (`id`, `description`, `steps`) → `ChainValidationError`
3. Empty steps list → `ChainValidationError`
4. Jinja2 syntax error in any step template → `ChainValidationError`
5. Pydantic schema validation → `ChainValidationError`

Invalid chains are **skipped** in `load_all()` with an error log (not fatal).

---

## ChainAugmentor

```python
augmentor = ChainAugmentor(model_router, security_manager)
result = await augmentor.run_chain(chain, ctx, initial_context={"code": "...", "file": "..."})

# result: ERSExecutionResult
result.success    # bool
result.outputs    # dict[str, str] — all step outputs by output_key
result.errors     # list[str]
result.chain_id   # str
```

**Execution flow:**
1. Requires `reasoning:elevated` capability from ctx at chain start.
2. Plans blocks: steps with same `batch_group` → single block; sequential steps → individual blocks.
3. Batch block: `asyncio.gather()` — concurrent in same event loop (not threads).
4. Sequential block: `await _run_step()`.
5. Each step: `child_context(f"ers:{step.id}", trust_ceiling=ctx.trust_level)`.
6. `finally:` block calls `child_ctx.revoke_task_grants()` — audit trail complete.
7. `on_failure="stop"` on any step → immediate chain abort with partial outputs.

**RAM gate:** If `psutil.virtual_memory().available < 1024 MB`, batch steps run serially even if `batch_group` set.

---

## Step Execution Detail

```python
# In each step:
tpl = Environment(undefined=StrictUndefined).from_string(step.prompt_template)
prompt = tpl.render(**execution_context)  # Raises UndefinedError if variable missing
response = await router.generate(
    model_alias=step.model_alias,
    prompt=prompt,
    stop=step.stop_sequences,
    max_tokens=step.max_tokens,
    ctx=child_ctx
)
outputs[key] = response[0]
execution_context[key] = response[0]  # Available to subsequent steps
```

**StrictUndefined:** Template variables that aren't in `execution_context` raise `TemplateError`, not NoneType. Chain fails cleanly.

---

## YAML Chain Writing Guide

```yaml
id: my_chain          # Must match filename convention (snake_case)
description: "What this chain does"

steps:
  - id: step_one
    prompt_template: |
      Do something with: {{ input_variable }}
      Be specific and precise.
    model_alias: reason    # see model aliases in BOOTSTRAP_MODELS.md
    output_key: step_one_result
    on_failure: stop       # ALWAYS set on critical steps

  - id: step_two
    prompt_template: |
      Use this previous result: {{ step_one_result }}
      Now do something else.
    model_alias: coder
    output_key: final_output
    # batch_group omitted → sequential step

# BATCH EXAMPLE:
  - id: check_syntax
    batch_group: parallel_checks     # Same group = parallel
    prompt_template: "Check syntax: {{ code }}"
    model_alias: coder
    output_key: syntax_result

  - id: check_logic
    batch_group: parallel_checks     # Runs alongside check_syntax
    prompt_template: "Check logic: {{ code }}"
    model_alias: reason
    output_key: logic_result

  - id: summarize                    # After batch completes
    prompt_template: "Syntax: {{ syntax_result }}\nLogic: {{ logic_result }}"
    model_alias: reason
    output_key: summary
```

---

## Invoking ERS from Python

```python
from lib.ers.chain import ChainLoader
from lib.ers.augmentor import ChainAugmentor
from lib.security.context import SecurityContext
import asyncio

loader = ChainLoader()
chain = loader.load_file("chains/clone/code_review.yaml")

ctx = SecurityContext.default("my_agent")
augmentor = ChainAugmentor(model_router, security_manager)

result = asyncio.run(augmentor.run_chain(chain, ctx, {
    "code": "def foo(): pass",
}))
print(result.outputs)
```

---

## Existing Chains — What They Expect

| Chain ID | Required initial_context keys | Output keys |
|----------|------------------------------|-------------|
| `clone_code_action` | `action_type`, `code_context`, `file_path`, `language` | `edit_plan`, `modified_code` |
| `clone_code_review` | `code` | `syntax_findings`, `logic_findings`, `security_findings`, `review_report` |
| `research_deep` | `query` | (chain-specific) |
| `git_summarize` | `diff` or `commits` | `summary` |
| `nixos_verify` | `config_path` or `config_text` | `validation_result` |
| `debug_error` | `error_message`, `context_code` | `diagnosis`, `fix` |

---

## Known Issues

- `code_action.yaml` and `code_review.yaml` have no `capabilities:` field — acceptable (uses defaults) but prevents audit verification per step.
- `code_action.yaml` steps have no `on_failure: stop` — if `action_planner` fails, `action_executor` runs with `{{ edit_plan }}` being undefined → Jinja2 `UndefinedError`.
