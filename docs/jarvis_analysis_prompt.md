# JARVIS REPOSITORY ANALYSIS PROMPT (V3 — March 2026)
> Paste this entire document into a new AI session, followed by the repository contents.
> The model needs no prior context — everything it needs to know is in this prompt.
> **V3 Note:** This prompt has been updated to reflect the post-V3-remediation state.
> Old bootstrap files (BOOTSTRAP v2.2–v2.5, JARVIS_FIX_BOOTSTRAP) have been purged.
> The canonical reference is `docs/BOOTSTRAP_V3.md`.

---

## YOUR ROLE

You are a senior systems architect performing a deep technical analysis of **Jarvis**, a personal AI orchestration system built for NixOS, running entirely on local hardware (Intel i7-1165G7, CPU-only, no GPU). The owner has been iteratively building this system with AI assistance and wants a comprehensive, honest, component-by-component analysis of the current state of the codebase.

You are not here to validate or reassure. You are here to give an expert read of every component: what it does, how well it does it, what's missing, what's subtly broken, and what's genuinely well-designed.

---

## SYSTEM BACKGROUND (do not skip — this is essential context)

### What Jarvis is

Jarvis is a **personal AI assistant / orchestration layer** that sits on top of local LLM inference (Ollama). It is not a web app or a commercial product. It is a daily-driver tool used by one developer on one NixOS machine.

### Hardware constraints that shape every design decision
- **CPU:** Intel i7-1165G7 (Tiger Lake, 4 cores / 8 threads)
- **RAM:** 16 GB — Ollama holding a 14B model consumes ~9 GB, leaving ~7 GB for everything else
- **Storage:** NixOS root + `/THE_VAULT/` (separate HDD for runtime data)
- **No GPU** — all inference is CPU-bound, 14B model takes 1–5 seconds per response

### The dual-directory layout (critical for understanding paths)
```
~/NixOSenv/Jarvis/        ← Source repository (code lives here)
/THE_VAULT/jarvis/        ← Runtime vault (databases, venv, context, secrets — heavy data, HDD)
```

### Core technology stack
| Layer | Technology |
|-------|-----------|
| Primary language | Python 3.12 |
| Neovim plugin | Lua |
| TUI monitor | Rust + Ratatui |
| Local inference | Ollama (qwen3:14b general, qwen3-coder:7b code) |
| Web search | SearXNG (self-hosted) |
| Storage | SQLite |
| Service management | systemd (NixOS) |
| External APIs | Anthropic, OpenAI, Google, DeepSeek, Groq, Mistral (all opt-in) |

### Architecture overview (v2 — what should exist if fully built)

The system has **five major subsystems**, implemented across phased development:

**1. Security Permission System** (`lib/security/`)
Replaces a crude three-mode flag system (private/internal/public) with a principled capability-based access control model.
- `TrustLevel`: UNTRUSTED(0) → BASIC(1) → ELEVATED(2) → ADMIN(3) → SYSTEM(4)
- 20+ namespaced capabilities: `chat:basic`, `ide:read`, `ide:edit`, `fs:validate`, `fs:exec`, `vault:write`, `net:search`, `model:local`, `model:external`, `reasoning:elevated`, etc.
- `SecurityContext`: holds agent_id, trust_level, list of `CapabilityGrant` objects
- `CapabilityGrant`: capability name, granted_at, expires_at, scope (task/session/persistent), audit_token
- `CapabilityGrantManager`: evaluates requests, handles interactive prompts, OOB (out-of-band) approval via pending_grants table when no TTY available
- `CapabilityPending`: exception raised when no TTY is available — caller must handle, not crash
- `GrantStore`: serializes/restores persistent grants across process restarts
- `AuditLogger`: writes ALL capability events (granted/denied/revoked/pending) to `security_audit.db`
- Shadow mode: during Phase 1 rollout, denials are logged but not enforced (prevents bricking)
- Clone isolation: child SecurityContext trust_level ≤ parent (enforced in `add_grant()`)
- OOB approval: `jarvis approve <pending_id>` CLI command, `/security/resolve` HTTP endpoint
- **Known bugs fixed in bootstrap v2.1:** `scope` column added to `capability_events` table; `GrantStore` SQL corrected; `shadow_require()` catches both `CapabilityDenied` AND `TrustLevelError`

**2. External Reasoning System (ERS)** (`lib/ers/`)
Multi-step chained reasoning over existing prompts. Does NOT replace existing prompts — wraps them.
- Chain definitions: YAML files in `chains/` directory
- `ChainStep`: id, model, capabilities, prompt_template (Jinja2), action, quality_gate, trigger, batch_group, ram_gate_mb
- `ERSChain`: chain_id, description, seed_prompt, context_source, steps, on_failure
- `ChainLoader`: loads and validates YAML chains at load time (`ChainValidationError` on bad structure)
- `PromptSeedLoader`: wraps seed prompt in ERS envelope — seed text is byte-for-byte unchanged inside
- `ReasoningAugmentor`: executes chain step-by-step; handles capability requests per-step; Jinja2 for templates; batch parallelism with RAM gate (psutil); `simpleeval` for trigger expressions (NOT `eval()` — security fix); `on_failure` cleanup; task grants revoked in `finally`
- `ERSAccessProtocol`: per-step capability requesting
- Quality gates: confidence threshold → fallthrough to different step
- Batch parallelism: steps with same `batch_group` run in `ThreadPoolExecutor`; RAM gate (default 3000 MB free required); each thread gets its own child SecurityContext (thread-safe)
- `frozen_outputs` snapshot passed to batch threads (no shared mutable dict)

**3. External Model Hub** (`lib/models/`)
Unified adapter layer for local (Ollama) and external providers.
- `ModelAdapter` ABC: `call(model, prompt, max_tokens) → (text, confidence)`
- `ModelRouter`: parses `"local/<model>"` and `"external/<provider>/<model>"` spec strings
- Providers: Ollama (always on), Anthropic, OpenAI, Google, DeepSeek, Groq, Mistral (all opt-in)
- Secrets: AES-256 in `/THE_VAULT/jarvis/secrets/.keyring` via `cryptography` library
- Cost estimation shown before external API calls
- Fallback chain: local model failure → external (if configured); external unavailable → local

**4. jarvis-lsp — Language Server + Security Bridge** (`services/jarvis_lsp.py`)
Minimal LSP server + HTTP sidecar, introduced in Phase 1.5 (before ERS) to solve the OOB approval problem.
- LSP: `pygls`, TCP port **8002** (NOT stdio — enables server persistence across Neovim restarts)
- HTTP sidecar: `FastAPI` + `uvicorn`, port **8001** (security bridge for Lua and CLI)
- Session token: `secrets.token_hex(16)` generated at CLI startup, written to `/THE_VAULT/jarvis/context/active_session_token` (mode 0600)
- Neovim reads token → passes via `initializationOptions.jarvis_session_token`
- `_get_clone_ctx()`: resolves token to parent SecurityContext → creates bounded child clone
- Multi-session: two Neovim windows get independent clone contexts per `conn_id`
- Long-poll: `GET /security/pending?wait=N` (max 30s) — avoids 60-curl-process poll loop
- Phase 4 additions: `textDocument/codeAction`, `textDocument/hover`, `textDocument/completion` (Incomplete Results pattern — returns empty list immediately, pushes results via `jarvis/completionReady` notification), `workspace/didChangeWatchedFiles`

**5. Antigravity IDE Layer** (`lua/jarvis/ide/`)
Neovim plugin extension. Zero modifications to existing `lua/jarvis/` files — purely additive.
- New commands: `:JarvisIDEFix`, `:JarvisIDEExplain`, `:JarvisIDERefactor`, `:JarvisIDETestGen`, `:JarvisIDEDocGen`, `:JarvisIDEChat`, `:JarvisIDEModel`, `:JarvisIDESearch`, `:JarvisIDECommit`, `:JarvisIDEReview`
- `lua/jarvis/ide/security.lua`: non-blocking async HTTP to port 8001 via `vim.fn.jobstart`
- OOB pending: long-poll with `?wait=10`, max 6 attempts (60s timeout), one active curl at a time
- Session token read from file at `M.setup()` time

**Key new files added in v2 (should all exist):**
```
lib/security/__init__.py
lib/security/context.py       # SecurityContext, CapabilityGrant, TrustLevel, CAPABILITY_TRUST_FLOOR
lib/security/grants.py        # CapabilityGrantManager, CapabilityRequest, CapabilityPending
lib/security/store.py         # GrantStore (persistent grant serialization)
lib/security/audit.py         # AuditLogger → security_audit.db (two tables)
lib/security/exceptions.py    # CapabilityDenied, TrustLevelError, CapabilityExpired
lib/security/secrets.py       # AES-256 keyring for API keys
lib/ers/__init__.py
lib/ers/chain.py              # ERSChain, ChainStep, ChainLoader, ChainValidationError
lib/ers/augmentor.py          # ReasoningAugmentor
lib/ers/seed_loader.py        # PromptSeedLoader
lib/ers/access_protocol.py    # ERSAccessProtocol
lib/models/__init__.py
lib/models/router.py          # ModelRouter
lib/models/adapters/base.py   # ModelAdapter ABC
lib/models/adapters/ollama.py
lib/models/adapters/anthropic.py
lib/models/adapters/openai.py
lib/models/adapters/gemini.py
lib/models/adapters/deepseek.py
lib/models/adapters/groq.py
services/jarvis_lsp.py        # pygls LSP server + FastAPI sidecar
lua/jarvis/ide/init.lua
lua/jarvis/ide/security.lua
lua/jarvis/ide/actions.lua
lua/jarvis/ide/lsp.lua
lua/jarvis/ide/inline.lua
lua/jarvis/ide/chat.lua
chains/research_deep.yaml
chains/debug_error.yaml
chains/git_summarize.yaml
chains/clone/code_action.yaml
chains/clone/code_review.yaml
lib/prompts/research_base.txt
lib/prompts/debug_triage.txt
lib/prompts/ide_action_base.txt
lib/prompts/git_summary_base.txt
config/security.toml
config/models.toml
requirements-v2.txt
scripts/migrate_modes.py
scripts/audit_capabilities.py
```

**Key databases in `/THE_VAULT/jarvis/databases/`:**
- `events.db` — existing, unchanged
- `knowledge.db` — existing, unchanged
- `security_audit.db` — new, two tables:
  - `capability_events(id, ts, agent_id, capability, action, scope, reason, granted_by, audit_token, auto, denial_reason)`
  - `pending_grants(id, ts, agent_id, capability, reason, scope, status)`

**Known resolved bugs (look for these fixes in the code):**
- BUG-1: `eval()` in trigger evaluation → replaced with `simpleeval.simple_eval()`
- BUG-2: `scope` column missing from `capability_events` → added; GrantStore SQL fixed
- BUG-3: batch parallel threads shared mutable `SecurityContext.grants` → fixed with per-thread child contexts and frozen `step_outputs` snapshot
- BUG-4: `shadow_require()` only caught `CapabilityDenied`, not `TrustLevelError` → both now caught
- GAP-5: Session token had no spec → fully implemented with `register_session()` / `_get_clone_ctx()`
- GAP-6: Lua poll loop spawned 60 curl processes → replaced with long-poll `?wait=10`
- GAP-7: New Python dependencies undeclared → `requirements-v2.txt` created
- GAP-8: `ChainLoader` had no load-time validation → `_validate()` added

---

## WHAT YOU MUST DO

Perform a **complete, component-by-component analysis** of the actual repository contents provided below. For every file and subsystem, cover:

### For each Python module:
1. **What it does** — the actual behavior, not the intended behavior
2. **Correctness** — does it actually work as designed? Look for logic errors, missing error handling, wrong assumptions
3. **Security posture** — any privilege escalation paths, injection risks, credential exposure
4. **Thread safety** — any shared mutable state accessed from multiple contexts
5. **NixOS compatibility** — any hardcoded paths, non-Nix-friendly patterns, venv issues
6. **Test coverage** — what is and isn't covered
7. **Refinements vs. bootstrap** — what did the developer add, change, or improve beyond the bootstrap spec?

### For each Lua module:
1. **Correctness** — does the async pattern work properly on Neovim's event loop?
2. **Error handling** — what happens when the HTTP sidecar is down?
3. **Session token handling** — is the token read correctly and passed correctly?
4. **Deviations** — what did the developer change from the spec?

### For each YAML chain:
1. **Schema compliance** — does it pass `ChainLoader._validate()`?
2. **Capability correctness** — do the capability requirements match what each step actually needs?
3. **Quality gate logic** — does the fallthrough logic make sense?
4. **Prompt template correctness** — valid Jinja2? Missing variables handled?

### For the Rust TUI:
1. **New tabs** — are Security, ERS, and IDE tabs implemented?
2. **Read-only DB access** — is `PRAGMA query_only = true` used?
3. **Compilation safety** — is `make rust-build` (with ollama unload) the only build path?

### Cross-cutting concerns:
1. **Phase completion** — which phases are actually complete vs. stubbed vs. missing?
2. **Dependency graph** — are all imports resolvable? Is `requirements-v2.txt` complete?
3. **`shadow_mode` status** — is it still `true` (Phase 1 safe) or has it been disabled for Phase 2?
4. **Migration status** — are old `config/private`, `config/internal`, `config/public` files deprecated properly?
5. **Security audit trail** — does the actual code produce correct audit events end-to-end?
6. **Unexpected additions** — anything the developer built that wasn't in the spec? Evaluate it.
7. **Regressions** — did any changes break existing v1 functionality (`/chat`, `/fix`, `/explain`, `/index`, `/cancel`)?

---

## OUTPUT FORMAT

Structure your analysis exactly as follows:

```
# JARVIS V2 — FULL REPOSITORY ANALYSIS

## Executive Summary
[3–5 sentences: overall state, what's done, what's not, biggest concern]

## Phase Completion Scorecard
[Table: Phase | Status | Gate Passable? | Notes]

## Component Analysis

### lib/security/
#### context.py
#### grants.py
#### store.py
#### audit.py
#### exceptions.py
#### secrets.py

### lib/ers/
#### chain.py
#### augmentor.py
#### seed_loader.py
#### access_protocol.py

### lib/models/
#### router.py
#### adapters/

### services/jarvis_lsp.py

### lua/jarvis/ide/

### chains/

### config/

### jarvis-monitor/ (Rust TUI)

### jarvis.py (root entrypoint)

### scripts/

### tests/

## Bug Status: Known Fixes Verified
[Table: Bug ID | Fixed? | Evidence | Any new issues introduced?]

## Undocumented Refinements
[What the developer added beyond the bootstrap spec — good, neutral, or concerning]

## Critical Issues Remaining
[Numbered list — severity, location, description, recommended fix]

## What's Genuinely Well-Built
[Honest praise for things done correctly]

## Recommended Next Actions
[Prioritized: what to fix before any further feature work]
```

---

## REPOSITORY CONTENTS

[PASTE THE REPOSITORY FILES BELOW THIS LINE]
