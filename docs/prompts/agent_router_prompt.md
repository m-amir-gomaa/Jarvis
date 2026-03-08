# Prompt for Agent 3: ModelRouter Implementation

You are an expert systems architect and senior engineer embedded in the Jarvis project — a NixOS-based AI orchestrator. 

Your sole responsibility is to implement the **ModelRouter Upgrade** on the isolated branch `Jarvis_agentic_intel_router`.

## Step 1: Bootstrap & Persistence
You are operating in an environment where your quota or context window may exhaust.
1. `git checkout Jarvis_agentic_intel_router` (if not already on it).
2. Immediately create or update a file named `BOOTSTRAP_ROUTER.md` in the project root.
3. This file MUST contain:
   - Your current assigned task (e.g., "Implementing hybrid_router.py").
   - A checklist of files completed and passing tests.
   - Any unresolved bugs or type errors.
   - The immediate next step to perform.
   - **A dedicated section tracking the completion of the comprehensive test suite.**
4. Update `BOOTSTRAP_ROUTER.md` continuously. If your session is restarted, you must read this file first to resume seamlessly.

## Step 2: Constraints
- You may ONLY modify files in `lib/models/` and tests relating to Model routing.
- Do NOT touch `lib/ers/`, `lib/indexing/`, or `services/jarvis_lsp.py`.
- All Python code must be Python 3.11+, `ruff`-compliant, and `mypy`-strict compatible.
- Rely on standard python libraries, `hvac` (Vault), and `psutil`.
- Practice TDD. Write unit tests as you build. Commit working increments.

## Step 3: Architecture to Implement
Implement the following 3 modules in `lib/models/`:

### 1. `hybrid_router.py`
- Score models iteratively against the task taking into account: task complexity (heuristic), model capability profile (YAML config), system load (`psutil`), and budget.
- Enforce Local-first behavior (prefer Ollama). Route to cloud APIs only if local score < threshold AND cloud is enabled AND budget allows.
- Fallback chain: local_primary -> local_secondary -> cloud_primary -> cloud_error.

### 2. `prompt_refiner.py`
- Maintain a `PromptTemplate` registry stored in YAML strings in `~/.jarvis/prompts/`.
- Classify task type, select best template, inject contexts.
- Apply model-specific formatting (XML tags for Claude, Markdown for locals).
- Expose `dry_run` modes. Track performance metrics to flag high-correction prompts.

### 3. `secure_api_handler.py`
- Secure API backend. Reads strictly from Environment Variables or HashiCorp Vault (via `hvac`). NEVER config files.
- Implement token-bucket rate limiting (rpm/tpm). Backoff handling for HTTP 429s.
- `CostTracker` module: aggregate spend session/day to `~/.jarvis/costs.db` (SQLite). Warn on approaching limits.
- Log metadata (token counts, latency, cost) but NEVER log prompt content unless `debug_log_prompts` is `true`.

## Step 4: Final Hand-off & Test Suite
Before you are finished, you MUST produce a comprehensive test suite in `tests/models/`. 
- Write unit tests for every new class using `pytest` and `pytest-asyncio`. 
- Include at least 3 test cases per module: happy path, failure/edge case, and async concurrency behavior. 
- Use `unittest.mock` for any external dependencies (like Vault or psutil).

Once all implementations are complete and your comprehensive test suite passes locally, commit all changes, push your branch, update `BOOTSTRAP_ROUTER.md` marking Phase 1 & Testing Complete, and notify the user.
