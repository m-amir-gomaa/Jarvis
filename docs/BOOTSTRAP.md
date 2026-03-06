# JARVIS PROJECT — AI SESSION BOOTSTRAP

**READ THIS FILE FIRST AT EVERY SESSION START.**
This file exists so that any AI session — even after quota exhaustion — can orient itself instantly and continue building the Jarvis system without losing context.

---

## 1. Who You Are Working With

- **User**: qwerty, running NixOS on a Dell Vostro 3510 (i7-1165G7, 16 GB DDR4, 800 GB `/THE_VAULT`, no dGPU — Intel Iris Xe only)
- **Tools**: Antigravity AI only. No other AI tools are used for this project.
- **Goal**: Build a fully local, self-improving AI engineering assistant called "Jarvis" — running entirely on this machine using Ollama, no cloud, no API costs.

---

## 2. The Two Files You Must Read

Before doing ANYTHING, read both of these files completely:

| File | Path | Purpose |
|---|---|---|
| **Master Spec** | `~/NixOSenv/Jarvis/docs/JARVIS_Specs_and_Roadmap_Final_Merged.md` | The implementation blueprint. Every MVP has a spec table, acceptance criteria, and an agent prompt to paste into Claude Code. |
| **This file** | `~/NixOSenv/Jarvis/docs/BOOTSTRAP.md` | Project state, what is done, what is next, and how to continue. |

> If you are mid-session and unsure what to do next, re-read these two files.

---

## 3. Filesystem Layout — Where Everything Lives

```
~/NixOSenv/               ← Git repo. ALL system configuration goes here.
├── configuration.nix      ← System packages, services.ollama, networking (Ollama CPU fixed)
├── home.nix               ← Dev tools via home-manager (rust-analyzer, pyright, nil...)
├── modules/
│   └── jarvis.nix         ← System AI optimizations (Nice=15, Swappiness=10, 4GB Swap)
├── Jarvis/                ← PROJECT SOURCE (now inside system repo)
│   └── docs/
│       ├── BOOTSTRAP.md   ← This file
│       └── JARVIS_Specs_and_Roadmap_Final_Merged.md ← Master spec
└── flake.nix              ← Already exists

/THE_VAULT/jarvis/         ← Runtime data, state, AI indexes. NOT in git.
├── .venv/                 ← Python virtualenv (create with: python -m venv .venv)
├── lib/                   ← ollama_client.py, event_bus.py, model_router.py, env_manager.py
├── tools/                 ← chunker.py, cleaner.py
├── pipelines/             ← ingest.py, optimizer.py, agent_loop.py, research_agent.py, nixos_validator.py
├── services/              ← git_summarizer.py, coding_agent.py, health_monitor.py, daily_digest.py, context_updater.py
├── config/
│   ├── models.toml        ← model aliases and digest pins
│   ├── user_context.md    ← 200-300 word identity file injected into every /chat
│   └── .env               ← OLLAMA_BASE_URL, ANYTHINGLLM_API_KEY, GITEA_WEBHOOK_SECRET (never commit)
├── inbox/                 ← Drop PDFs/markdown here → auto-processed by ingest daemon
├── logs/                  ← events.db, metrics.db, ingestion.jsonl, ollama.lock
├── prompts/               ← Prompt best.txt files and optimizer runs
├── index/                 ← nixosenv.db, codebase.db, documents.db (SQLite RAG indexes)
├── research/              ← MVP 8 web research summaries
├── review/                ← Escalation files from MVP 7, NixOS validator reports from MVP 10
└── Makefile               ← MVP 16: make test-all to validate the whole system
```

---

## 4. The Build Phases — Current Status

### ✅ DONE: Planning & Spec
- Full 17-MVP specification written and merged from multiple sources
- Hardware constraints researched and applied (i7-1165G7 performance table, RAM-aware keepalive, async IDE constraint, systemd lifecycle)
- All 7 refinements applied to existing MVPs
- MVPs 15 (user_context.md), 16 (Makefile), and 17 (env manager) added

### ✅ DONE: Phase 1 — NixOS Setup
- [x] Delete `local-ai.nix` and clean up configuration
- [x] Install dev tools via home-manager
- [x] Pull base models (`nomic-embed-text`, `mistral:7b`, `qwen3:1.7b`)
- [x] Mount and prepare `/THE_VAULT/jarvis/`
- [x] Create directory structure

### ✅ DONE: Phase 2 — Foundation MVPs
- [x] MVP 17: `lib/env_manager.py` (Validation & Secrets)
- [x] MVP 16: `Makefile` (Test Harness)
- [x] MVP 1: `lib/ollama_client.py` (Gateway & Concurrency Lock)
- [x] MVP 13 (Partial): `lib/event_bus.py` & `lib/model_router.py`

### ✅ DONE: Phase 3 — Document Pipeline
- [x] MVP 2: `tools/chunker.py` (Semantic Chunker)
- [x] MVP 3: `tools/cleaner.py` (NotebookLM Optimizer)
- [x] MVP 4: `lib/anythingllm_client.py` (Vector DB Integration)
- [x] MVP 5: `pipelines/ingest.py` (Orchestrated Ingestion)

### [/] IN PROGRESS: Phase 4 — Intelligence Layer
- [x] MVP 6: `pipelines/optimizer.py` ← JUST COMPLETED
- [x] MVP 7: `pipelines/agent_loop.py` (Multi-turn reasoning & Thinking Mode verified)
- [x] MVP 8: `lib/git_summarizer.py`
- [x] MVP 10: `lib/nix_validator.py`
- [x] Resource Management: `jarvis.py` (SIGSTOP/SIGCONT priority control)
- [x] MVP 11: `services/health_monitor.py` (Extended pause tracking)
- [x] MVP 14: `services/git_monitor.py`

### ✅ DONE: Phase 5 — Full Agent Integration
- [x] Systemd user services for all daemons (in `modules/jarvis.nix`)
- [x] MVP 12: `services/coding_agent.py` + Neovim plugin (`lua/jarvis/`)
- [x] MVP 13 (Complete): `services/daily_digest.py` + `services/context_updater.py`

### ✅ DONE: Phase 6 — Rust Dashboard & Polish
- [x] MVP 14: Rust Ratatui TUI dashboard (`jarvis-monitor`)
- [x] MVP BIG: Natural language CLI router (`jarvis` unified CLI)
- [x] Final system integration test (`make test-all`)

---

## 5. How to Use the Master Spec

1. Open `JARVIS_Specs_and_Roadmap_Final_Merged.md`
2. Find the MVP you are about to implement (e.g., `# MVP 1 — Ollama Gateway`)
3. Read the spec table, public interface, and acceptance criteria
4. Copy the **AGENT PROMPT** at the end of that MVP section
5. In a new Claude Code session: paste the agent prompt + any relevant context → it will implement the file
6. Run `make test-mvpN` to verify the acceptance criteria pass
7. Check this BOOTSTRAP.md and update the phase checklist above (mark `[x]` for done)

---

## 6. Key Technical Decisions (Never Reverse These)

| Decision | Reasoning |
|---|---|
| `mineru[pipeline]` NOT `mineru[all]` | No GPU on this machine. `[all]` pulls CUDA deps that fail to build. |
| home-manager for LSP servers, NOT mason.nvim | mason downloads ELF binaries that reference `/lib/ld-linux.so` — does not exist on NixOS |
| `keep_alive: 0` for mistral:7b after each call | Frees 5 GB RAM immediately; DO NOT keep it loaded between background tasks |
| `keep_alive: "5m"` for qwen3:14b during coding | Keep loaded during active session; 30s cold start is too slow |
| Ollama Concurrency Lock (`ollama.lock`) | Prevents multiple models loading at once; avoids 16GB RAM overflow crash |
| All subprocess calls: list-form + timeout= | NEVER shell=True with model output — shell injection risk |
| systemctl --user for service lifecycle | NOT subprocess.Popen — prevents zombie processes eating RAM |
| plenary.curl async in Neovim Lua | NEVER vim.fn.system() — will freeze Neovim for 30-90s during CPU inference |
| DELETE local-ai.nix | References CUDA packages — completely broken on i7-1165G7 (Intel Iris Xe, no NVIDIA) |

---

## 7. Model Reference

| Model | Task | Speed | RAM | keep_alive |
|---|---|---|---|---|
| `qwen3:14b-q4_K_M` | fix, chat, diagnose, reason | ~3-5 tok/s | ~9-10 GB | `"5m"` during coding, `0` otherwise |
| `mistral:7b-instruct-q4_K_M` | clean, summarize, classify, score | ~6-10 tok/s | ~5 GB | `0` always — free after use |
| `qwen3:1.7b` | FIM autocomplete only | ~25-40 tok/s | ~1.4 GB | `"10m"` — tiny, keep loaded |
| `nomic-embed-text` | embeddings | instant | ~0.3 GB | always loaded |

---

## 8. Services & Ports

| Service | Port/Path | Start command |
|---|---|---|
| Ollama | localhost:11434 | `systemctl start ollama` |
| AnythingLLM | localhost:3001 | (Static Binary) |
| SearXNG | localhost:8888 | `systemctl start searx` |
| health_monitor | (Event Bus) | `systemctl --user start jarvis-health-monitor` |
| git_monitor | (Event Bus) | `systemctl --user start jarvis-git-monitor` |
| Event Bus | `events.db` | System-wide observability source of truth |
| jarvis CLI | `jarvis.py` | `jarvis pause` / `resume` / `status` |

---

## 9. If You Are Resuming After Quota Exhaustion

1. Read this file (`BOOTSTRAP.md`) completely
2. Read the relevant MVP section in `JARVIS_Specs_and_Roadmap_Final_Merged.md`
3. Check the Phase checklist in section 4 — currently at **Phase 4/5**.
4. Run `make test-all` from `/THE_VAULT/jarvis/` to verify system health.
5. If anything is unclear, show qwerty this file and ask them for guidance.

---

*Last updated: 2026-03-05. Phases 1–5 COMPLETED. Remaining: Phase 6 (Rust dashboard) + final integration test.*
