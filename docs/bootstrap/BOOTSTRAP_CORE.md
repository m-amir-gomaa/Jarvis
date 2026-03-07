# JARVIS BOOTSTRAP — CORE SYSTEM REFERENCE
**Version:** V3 (March 2026) | **Commit anchor:** `cf65cfe` | **Status:** Active daily-driver

> READ THIS FIRST. Every other bootstrap file references this one.
> This file is the map. Start here, go deeper with the specialist files.

---

## 1. What Is Jarvis

A personal AI orchestrator for ONE developer on ONE NixOS machine.
- Not a web service. Not multi-user. Not a product.
- All inference is CPU-bound (no GPU). Latency is 1–5s per response.
- Privacy-first: local model by default, external APIs opt-in per-request.

---

## 2. Hardware & Constraints

| Resource | Spec | Impact |
|----------|------|--------|
| CPU | Intel i7-1165G7, 4C/8T | All inference serialized |
| RAM | 16 GB | Ollama 14B holds ~9 GB; 7 GB left |
| GPU | None | No CUDA/ROCm. CPU-only |
| Storage | NixOS SSD + `/THE_VAULT/` HDD | Heavy data on vault |

Ollama models in use:
- `qwen3:14b-q4_K_M` — reasoning/chat (heavy, ~9 GB)
- `qwen2.5-coder:7b-instruct` — code tasks (lighter, ~4 GB)
- `qwen3:8b` — fast chat
- `qwen3:1.7b` — completions/embed

**RAM gate in ERS:** If free RAM < 1024 MB, batch steps serialize instead of parallelizing.

---

## 3. Directory Layout (CRITICAL)

```
~/NixOSenv/Jarvis/          ← SOURCE REPOSITORY (git)
  jarvis.py                 ← Main CLI entrypoint (1389 lines)
  lib/                      ← Python library modules
    security/               ← Capability engine (V2)
    ers/                    ← External Reasoning System (V2)
    models/                 ← Model adapter hub (V2)
    llm.py                  ← V1 LLM wrapper (still in use by CLI)
    model_router.py         ← V1 privacy-based routing (still used)
    budget_controller.py    ← Token/cost budget tracking
    knowledge_manager.py    ← SQLite RAG knowledge base
    event_bus.py            ← Inter-component event system
    ollama_client.py        ← Direct Ollama http client (V1)
  services/
    jarvis_lsp.py           ← LSP server (port 8002) + HTTP sidecar (8001)
  lua/jarvis/               ← Neovim plugin (V1 core)
    ide/                    ← IDE extension (V2, additive only)
      security.lua          ← Capability bridge (HTTP to port 8001)
      actions.lua           ← 10 IDE actions with cap guards
      lsp.lua               ← LSP client setup + conn_id sync
      inline.lua            ← Ghost-text completions (debounce NOT WIRED)
      chat.lua              ← Chat buffer
      init.lua              ← Module init + keybinds
  chains/                   ← ERS YAML chain definitions
  config/                   ← TOML config files
  tests/                    ← Test suite
  tools/                    ← Test helper scripts
  scripts/                  ← Utility scripts
  jarvis-monitor/           ← Rust TUI dashboard (Ratatui)
  docs/bootstrap/           ← THIS DIRECTORY — bootstrap suite
  requirements-v2.txt       ← Python deps for V2 subsystems

/THE_VAULT/jarvis/          ← RUNTIME VAULT (persistent, HDD)
  databases/                ← ALL sqlite databases
    api_usage.db            ← Budget/token tracking
    security_audit.db       ← Capability grants, audit log, pending
    knowledge.db            ← RAG knowledge base
    events.db               ← System event log
    sessions.db             ← Persistent grants across restarts
  context/
    active_session_token    ← 32-char hex token (mode 0600)
  secrets/
    .keyring                ← AES-256 encrypted API keys
  .venv/                    ← Python virtual environment
```

**Key env vars (must be set in NixOS environment):**
```
JARVIS_ROOT=/home/qwerty/NixOSenv/Jarvis
VAULT_ROOT=/THE_VAULT/jarvis
```

---

## 4. Technology Stack

| Layer | Technology |
|-------|-----------|
| CLI | Python 3.12 (`jarvis.py`) |
| Security engine | `lib/security/` — capability-based RBAC |
| Reasoning | `lib/ers/` — YAML-driven chain executor |
| Model dispatch | `lib/models/` — async adapter hub |
| Neovim plugin | Lua (V1 core + V2 additive IDE layer) |
| Monitor TUI | Rust + Ratatui (`jarvis-monitor/`) |
| Local inference | Ollama (systemd user service) |
| Web search | SearXNG (self-hosted) |
| Storage | SQLite (all databases) |
| Service manager | systemd --user |
| External APIs | Anthropic, OpenAI, Google, DeepSeek, Groq, Mistral |

---

## 5. Subsystem Architecture (V2)

```
          jarvis.py (CLI)
               │
         ┌─────┴───────────────────────────────┐
         │                                      │
    V1 path (intent dispatch)          V2 commands (approve/pending)
    lib/llm.py + lib/model_router.py   lib/security/ engine
         │
    ┌────┴──────────┐
    │               │
 Ollama         Pipelines
 (local)    (agent_loop, research,
             nixos_validator, etc.)

services/jarvis_lsp.py
    ├── FastAPI HTTP (port 8001)    ← Security bridge for Lua + CLI
    │   ├── /ide/* (10 routes)
    │   ├── /security/request
    │   ├── /security/pending (long-poll)
    │   ├── /security/resolve
    │   └── /auth/conn_id
    └── pygls LSP (port 8002)      ← Neovim LSP client

lib/security/                      ← Capability engine
lib/ers/                           ← Chain reasoning
lib/models/                        ← Adapter hub
    adapters: ollama, anthropic, openai, gemini, deepseek, groq, mistral
```

---

## 6. Trust Level System

```
UNTRUSTED (0) → BASIC (1) → ELEVATED (2) → ADMIN (3) → SYSTEM (4)

LSP anonymous session:  trust=1 (BASIC)
LSP authenticated:      trust=2 (ELEVATED)
CLI session:            trust=3 (ADMIN)  ← but NOT USING SECURITY ENGINE YET
```

Who gets what automatically:
- BASIC: `model:local`, `chat:basic`, `ide:read` (auto-granted)
- ELEVATED: can request `ide:edit`, `vcs:read`, `net:search`, `model:external`, `reasoning:elevated`
- ADMIN: can request `fs:exec`, `vcs:write`, `vault:delete`, `security:grant`
- SYSTEM: `system:daemon` only

---

## 7. Service Ports

| Service | Port | Protocol |
|---------|------|---------|
| Ollama | 11434 | HTTP |
| SearXNG | 8080 | HTTP |
| Jarvis HTTP sidecar | 8001 | HTTP (FastAPI) |
| Jarvis LSP | 8002 | TCP (pygls) |

---

## 8. Build & Run Commands

```bash
# Virtual environment (always activate first)
source /THE_VAULT/jarvis/.venv/bin/activate

# Setup
make setup          # pip install -r requirements-v2.txt
make rust-build     # cargo build --release + copy to bin/

# Tests (run from ~/NixOSenv/Jarvis/)
make test-all       # Full suite
make test-security  # lib/security/ tests only
make test-ers       # lib/ers/ tests only
make test-router    # V1 model router test

# Services
jarvis start        # Start all systemd user services
jarvis stop         # Stop all
jarvis status       # Health check

# LSP sidecar (manual start for debugging)
python services/jarvis_lsp.py

# Monitor TUI
jarvis dashboard    # or: bin/jarvis-monitor
```

---

## 9. Session Token Flow

1. `jarvis.py` generates `secrets.token_hex(16)` on startup if absent.
2. Written to `/THE_VAULT/jarvis/context/active_session_token` (mode 0600).
3. Neovim reads token from file in `jarvis.lua` plugin setup.
4. Token passed via LSP `initializationOptions.jarvis_session_token`.
5. `_get_clone_ctx()` in `jarvis_lsp.py` validates token → assigns trust=2 if match, trust=1 if no/bad token.
6. 500ms after LSP attach, Lua fetches `/auth/conn_id` → stores in `_conn_id` for OOB long-poll isolation.

---

## 10. V3 State (What Was Just Done)

All fixes from `JARVIS_V2_PostPatch_Analysis.docx.md` applied:
- ✅ Trust ceiling bug fixed (P1-5)
- ✅ Database paths to `/databases/` (P1-6)
- ✅ conn_id wiring in lsp.lua (P1-7)
- ✅ Capability guards on explain/review (P2)
- ✅ OpenAI adapter positional arg (P2)
- ✅ Test suite aligned to current signatures
- ✅ Old bootstrap files purged

**Still TODO** — see `BOOTSTRAP_BUGS.md` for prioritized list.

---

## 11. Bootstrap Suite Index

| File | Read When |
|------|-----------|
| **BOOTSTRAP_CORE.md** (this file) | Always — start here |
| **BOOTSTRAP_SECURITY.md** | Working on capability engine, OOB flow, grants |
| **BOOTSTRAP_ERS.md** | Working on chains, augmentor, YAML definitions |
| **BOOTSTRAP_MODELS.md** | Working on adapters, routing, external APIs |
| **BOOTSTRAP_IDE.md** | Working on Lua plugin, LSP sidecar, Neovim integration |
| **BOOTSTRAP_BUGS.md** | At session start — prioritized active bug list |
| **BOOTSTRAP_TESTS.md** | Before running tests or adding test coverage |
| **BOOTSTRAP_CLI_MIGRATION.md** | Working on the V1→V2 CLI migration (next major task) |
