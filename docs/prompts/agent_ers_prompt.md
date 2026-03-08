# Prompt for Agent 1: ERS Subsystem Implementation

You are an expert systems architect and senior engineer embedded in the Jarvis project — a NixOS-based AI orchestrator. 

Your sole responsibility is to implement the **External Reasoning System (ERS) Upgrade** on the isolated branch `Jarvis_agentic_intel_ers`.

## Step 1: Bootstrap & Persistence
You are operating in an environment where your quota or context window may exhaust.
1. `git checkout Jarvis_agentic_intel_ers` (if not already on it).
2. Immediately create or update a file named `BOOTSTRAP_ERS.md` in the project root.
3. This file MUST contain:
   - Your current assigned task (e.g., "Implementing yaml_schema.py").
   - A checklist of files completed and passing tests.
   - Any unresolved bugs or type errors.
   - The immediate next step to perform.
   - **A dedicated section tracking the completion of the comprehensive test suite.**
4. Update `BOOTSTRAP_ERS.md` continuously. If your session is restarted, you must read this file first to resume seamlessly.

## Step 2: Constraints
- You may ONLY modify files in `lib/ers/` and tests relating to ERS.
- Do NOT touch `lib/indexing/`, `lib/models/`, or `services/jarvis_lsp.py`.
- All Python code must be Python 3.11+, `ruff`-compliant, and `mypy`-strict compatible.
- Rely on standard Python libraries, plus `pydantic` v2, `aiosqlite`, and `pytest-asyncio`. No other external cloud dependencies are permitted unless configured behind a strict offline toggle.
- Practice TDD. Write unit tests as you build. Commit working increments.

## Step 3: Architecture to Implement
Implement the following 5 modules in `lib/ers/`:

### 1. `yaml_schema.py`
Define the enhanced YAML chain schema using Pydantic v2. Support:
- `steps[]`: `id`, `tool`, `inputs`, `outputs`, `parallel_group`, `timeout_seconds`, `allow_partial`, `on_failure: [retry | substitute | correct | skip | abort]`.
- `conditionals[]`: Jinja2 expression evaluation for branching.
- `tool_chain[]`: syntactic sugar for linear pipelines.
- `external_apis[]` and `metrics` blocks.

### 2. `metrics_collector.py`
- Track per-step and per-chain latency, token usage, tool success/failure, correction attempts.
- Expose `generate_report()`.
- Store metrics in a local SQLite DB (`~/.jarvis/metrics.db`) via `aiosqlite`.

### 3. `self_correction.py`
- Implement `SelfCorrectionLoop`. Upon a step failure, use an LLM meta-prompt to diagnose and produce a corrected tool call/input.
- Score attempts; max 3 retries; log all diffs to MetricsCollector.

### 4. `adaptive_router.py`
- Wrap chain execution. Dynamically route around failures based on the YAML `on_failure` policies.
- Support tool substitution via a `ToolRegistry` semantic lookup.

### 5. `parallel_executor.py`
- Support `parallel_group` execution via `asyncio.gather`.
- Manage state via a thread-safe `ChainContext` (`asyncio.Lock`).
- Handle `group_failure_policy`.

## Step 4: Final Hand-off & Test Suite
Before you are finished, you MUST produce a comprehensive test suite in `tests/ers/`. 
- Write unit tests for every new class using `pytest` and `pytest-asyncio`. 
- Include at least 3 test cases per module: happy path, failure/edge case, and async concurrency behavior. 
- Use `unittest.mock` for any external dependencies.

Once all implementations are complete and your comprehensive test suite passes locally, commit all changes, push your branch, update `BOOTSTRAP_ERS.md` marking Phase 1 & Testing Complete, and notify the user.
