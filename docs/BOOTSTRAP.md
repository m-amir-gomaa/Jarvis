# JARVIS PROJECT — AI SESSION BOOTSTRAP v2.0
<!-- AGENT: Read every word of this file before touching any code. -->

**READ THIS FILE FIRST AT EVERY SESSION START.**
This file is the single source of truth for any AI coding agent (Claude Code,
Continue.dev, or any LLM with tool access) to orient itself, understand what
exists, what is broken, and what to build next — without losing context across
sessions or quota resets.

---

## ╔══ CODING AGENT MASTER PROMPT ══╗

> **Copy everything inside this box and paste it as your first message to the
> coding agent at the start of every session.** It fully bootstraps the agent's
> understanding of the project, hardware, constraints, and current task.

```
You are a senior AI systems engineer implementing "Jarvis" — a personal AI
operating system running on NixOS (i7-1165G7, 16GB DDR4, CPU-only inference,
no dGPU, Intel Iris Xe only). You are continuing an in-progress build.

═══════════════════════════════════════════════════════════════════════════════
STEP 1 — ORIENT YOURSELF (do this before any code)
═══════════════════════════════════════════════════════════════════════════════

1. Read docs/BOOTSTRAP.md completely (you are reading it now).
2. Run: make status      → see which services are live
3. Run: make test-all    → confirm current test suite passes
4. Run: jarvis status    → check Ollama health and loaded models
5. Run: git log --oneline -10 → see recent commits

Only after these 5 steps should you proceed to the current task in Section 6.

═══════════════════════════════════════════════════════════════════════════════
STEP 2 — UNDERSTAND THE HARDWARE CONSTRAINTS (never violate these)
═══════════════════════════════════════════════════════════════════════════════

CPU:  Intel i7-1165G7 — 8 threads, no AVX-512, CPU-only inference
RAM:  16GB DDR4 — CRITICAL CEILING. OS + services consume ~2GB baseline.
      Usable for models: ~10-11GB. NEVER load two large models simultaneously.
GPU:  NVIDIA MX350 (2GB VRAM) + Intel Iris Xe — BOTH UNUSABLE for LLM inference.
      Ollama runs 100% on CPU. Do NOT add CUDA, ROCm, or GPU offload code.
SSD:  ~/NixOSenv/ — source code, indices, .venv (fast I/O, limited space)
HDD:  /THE_VAULT/ — databases, bulk data, backups (slow I/O, large space)
OS:   NixOS with Flakes + Home Manager. Desktop: Hyprland (Wayland).

MODEL RAM BUDGET (memorize this — it governs all routing decisions):
  qwen3:1.7b-q4_K_M       → 1.3GB  | 30-45 tok/s | keep_alive: "10m"
  qwen3:8b-q4_K_M         → 5.5GB  | 8-12 tok/s  | keep_alive: "5m"
  qwen2.5-coder:7b-instruct→ 5.2GB  | 9-13 tok/s  | keep_alive: "5m"
  qwen3:14b-q4_K_M        → 9.5GB  | 3-5 tok/s   | keep_alive: "5m" active / "0" idle
  nomic-embed-text         → 0.3GB  | instant     | keep_alive: always

CRITICAL RAM RULE: qwen3:14b (9.5GB) + OS (2GB) = 11.5GB.
  → If ANY other model is also loaded → SWAP → system freeze.
  → The keep_alive="0" for background tasks is MANDATORY, not optional.
  → NEVER load reason + chat models simultaneously in any code path.

═══════════════════════════════════════════════════════════════════════════════
STEP 3 — UNDERSTAND THE CODEBASE LAYOUT
═══════════════════════════════════════════════════════════════════════════════

JARVIS_ROOT = ~/NixOSenv/Jarvis/   (set via env var, NOT hardcoded)

jarvis.py                    ← CLI entry point + intent classifier + routing
lib/
  ollama_client.py           ← Ollama REST wrapper (chat, generate, embed)
  model_router.py            ← Task→model mapping (needs v2 upgrade — see §6)
  knowledge_manager.py       ← 3-layer SQLite RAG (chunks table)
  episodic_memory.py         ← Cross-session event memory (events.db)
  event_bus.py               ← emit() / query() system log
  env_manager.py             ← Secrets + env var loader
  git_summarizer.py          ← Git commit summarizer
  nix_validator.py           ← NixOS config validator
  anythingllm_client.py      ← Legacy vector DB client (being replaced)
  ── TO BUILD ──
  budget_controller.py       ← API quota tracker + enforcer  [PHASE 1]
  cloud_client.py            ← Anthropic API wrapper          [PHASE 2]
  llm.py                     ← Unified local+cloud interface  [PHASE 2]
  working_memory.py          ← Cross-session chat persistence [PHASE 3]
  tools.py                   ← Tool registry + executor       [PHASE 4]
  semantic_memory.py         ← sqlite-vec RAG upgrade         [PHASE 5]

pipelines/
  agent_loop.py              ← Plan→Execute orchestrator (needs ReAct upgrade)
  research_agent.py          ← SearXNG-backed research
  ingest.py                  ← Document ingestion
  query_knowledge.py         ← RAG query runner
  doc_learner.py             ← URL/file → knowledge.db
  material_ingestor.py       ← Full research + ingest pipeline
  language_learner.py        ← Assisted language learning
  optimizer.py               ← Prompt optimizer

services/
  coding_agent.py            ← HTTP server :7002 (Neovim backend)
  health_monitor.py          ← systemd watchdog
  git_monitor.py             ← Git event emitter
  self_healer.py             ← Auto-restart failed services
  daily_digest.py            ← Morning summary generator
  context_updater.py         ← Background context refresh

tools/
  chunker.py                 ← Semantic text chunker
  cleaner.py                 ← Document cleaner (NotebookLM prep)

lua/jarvis/                  ← Neovim plugin (Lua)
jarvis-monitor/              ← Rust TUI dashboard (Ratatui)
config/
  models.toml                ← Model alias → Ollama model name mapping
  budget.toml                ← [TO CREATE] API quota limits    [PHASE 1]
  user_context.md            ← User identity context (injected into prompts)

data/
  knowledge.db               ← 3-layer RAG knowledge base
  api_usage.db               ← [TO CREATE] Cloud API usage log [PHASE 1]
  sessions.db                ← [TO CREATE] Working memory      [PHASE 3]

logs/
  events.db                  ← Event bus (episodic memory source)
  history.jsonl              ← CLI command log (NOT loaded back — known bug)

═══════════════════════════════════════════════════════════════════════════════
STEP 4 — KNOWN BUGS (fix these if you encounter them, they are pre-approved)
═══════════════════════════════════════════════════════════════════════════════

BUG-1 [CRITICAL] Hard-coded username
  All paths use "/home/qwerty" and "/home/qwerty/NixOSenv/Jarvis".
  Fix: BASE_DIR = Path(os.environ.get("JARVIS_ROOT", Path(__file__).parent.resolve()))
  Apply to: every file that has /home/qwerty or /home/qwerty/NixOSenv/Jarvis hardcoded.

BUG-2 [HIGH] Variable shadow in jarvis.py main()
  `command` is reassigned 3 times before the NLP routing path.
  The HIGH_RISK_INTENTS safety check uses the wrong value.
  Fix: rename intermediate assignments to `raw_command`, `cmd_lower`, etc.

BUG-3 [HIGH] AgentLoop ignores max_iterations
  `for i, step in enumerate(plan)` iterates ALL steps, ignoring the arg.
  Fix: `for i, step in enumerate(plan[:max_iterations]):`

BUG-4 [MEDIUM] EpisodicMemory not injected into regular chat
  get_session_context() is only used in AgentLoop, not in plain CLI chat.
  Fix: load last 5 turns from history.jsonl into system prompt on every call.

═══════════════════════════════════════════════════════════════════════════════
STEP 5 — ABSOLUTE RULES (never violate, never negotiate)
═══════════════════════════════════════════════════════════════════════════════

RULE-1: NO hardcoded paths. Use JARVIS_ROOT env var or Path(__file__).parent.
RULE-2: NO shell=True in subprocess calls. Always use list form + timeout=.
RULE-3: NO simultaneous loading of qwen3:14b + any other large model.
RULE-4: NO CUDA/ROCm/GPU code. This machine has no usable GPU for inference.
RULE-5: NO cloud API calls without BudgetController.check_and_reserve() first.
         Until BudgetController exists (Phase 1), NO cloud calls at all.
RULE-6: NO vim.fn.system() in Lua. Use plenary.curl async — always.
RULE-7: NO subprocess.Popen for service lifecycle. Use systemctl --user.
RULE-8: NO mineru[all]. Use mineru[pipeline] only — [all] pulls CUDA deps.
RULE-9: Every agent action that modifies a file MUST git commit before editing.
RULE-10: Every new module MUST have a corresponding make test-<name> target.

═══════════════════════════════════════════════════════════════════════════════
STEP 6 — CURRENT TASK (check Phase Status in §4 of BOOTSTRAP.md)
═══════════════════════════════════════════════════════════════════════════════

After completing Steps 1-5, go to Section 4 of docs/BOOTSTRAP.md.
Find the first item marked [ ] (not done) in the current phase.
That is your task. Read its full spec below (Section 7 of BOOTSTRAP.md).
Implement it. Run its test. Mark it [x]. Commit with message:
  "feat(phase-N): implement <component-name>"
Then proceed to the next [ ] item.

If you finish the current phase completely, update the phase status in
BOOTSTRAP.md and move to the next phase.
```

---

## 1. Project Identity

| Field         | Value                                                          |
|---------------|----------------------------------------------------------------|
| Project       | Jarvis — Personal AI Operating System                         |
| User          | m-amir-gomaa (NixOS, i7-1165G7, 16GB RAM, CPU-only inference) |
| Repo          | ~/NixOSenv/Jarvis/  (git remote: github.com/m-amir-gomaa/Jarvis) |
| Vault         | /THE_VAULT/  (HDD — bulk data, backups, databases)            |
| OS            | NixOS with Flakes + Home Manager · Hyprland (Wayland)         |
| AI Tools      | Claude Code (primary) · Jarvis self-improvement loop          |
| Architecture  | Local-first · Ollama inference · Budget-gated cloud fallback  |

---

## 2. Filesystem Layout

```
~/NixOSenv/
├── configuration.nix          ← system packages, services.ollama
├── modules/jarvis.nix         ← systemd user service definitions
├── flake.nix
└── Jarvis/                    ← JARVIS_ROOT (set this env var)
    ├── jarvis.py              ← CLI entry point
    ├── Makefile               ← test harness
    ├── config/
    │   ├── models.toml        ← model aliases
    │   ├── budget.toml        ← [TO CREATE] API quota config
    │   ├── codebases.toml     ← [TO CREATE] Privacy tracking for explicitly marked codebases
    │   └── user_context.md    ← identity injected into prompts
    ├── lib/                   ← core logic modules
    ├── pipelines/             ← orchestration pipelines
    ├── services/              ← systemd daemon services
    ├── tools/                 ← document processing tools
    ├── lua/jarvis/            ← Neovim plugin
    ├── jarvis-monitor/        ← Rust TUI dashboard
    ├── data/                  ← SQLite databases (on SSD)
    │   ├── knowledge.db       ← 3-layer RAG
    │   ├── api_usage.db       ← [TO CREATE] budget tracking
    │   └── sessions.db        ← [TO CREATE] working memory
    ├── index/
    │   └── codebase.db        ← code RAG index
    └── logs/
        ├── events.db          ← event bus / episodic memory
        └── history.jsonl      ← CLI command log

/THE_VAULT/
├── JarvisBackups/             ← compressed archives
└── jarvis/                    ← legacy path (migrate away from this)
```

---

## 3. Services & Ports

| Service              | Port / Path        | Start Command                                        |
|----------------------|--------------------|------------------------------------------------------|
| Ollama               | localhost:11434    | `systemctl start ollama`                             |
| SearXNG              | localhost:8888     | `systemctl start searx`                              |
| coding_agent         | localhost:7002     | `systemctl --user start jarvis-coding-agent`         |
| health_monitor       | events.db          | `systemctl --user start jarvis-health-monitor`       |
| git_monitor          | events.db          | `systemctl --user start jarvis-git-monitor`          |
| self_healer          | events.db          | `systemctl --user start jarvis-self-healer`          |
| daily_digest         | events.db          | `systemctl --user start jarvis-daily-digest`         |
| jarvis-monitor (TUI) | terminal           | `jarvis dashboard`                                   |

---

## 4. Phase Build Status

### ✅ COMPLETED: Legacy Phases 1–6

All original 17 MVPs are implemented. The system has:
- Ollama client with retry, streaming, keep_alive management
- Qwen3 /think and /no_think integration
- BM25 + vector RRF hybrid RAG in coding_agent.py
- 3-layer SQLite knowledge base (knowledge.db)
- Episodic memory (events.db via event_bus.py)
- Agent loop with plan→execute (text-only, no tool calls yet)
- Neovim plugin (FIM, /chat, /fix, /explain endpoints)
- Rust TUI dashboard (Ratatui, reads events.db)
- 4 systemd user services
- SearXNG-backed research pipeline
- Self-healer daemon
- NixOS config validator
- Git summarizer

---

### 🔴 PHASE 0 — Bug Fixes (Priority: CRITICAL · Est: 1-2 days)

> Fix before anything else. These are pre-approved changes.

- [ ] **BUG-1**: Remove all `/home/qwerty` and `/home/qwerty/NixOSenv/Jarvis` hardcodes
      - Replace with `JARVIS_ROOT = Path(os.environ.get("JARVIS_ROOT", Path(__file__).parent.resolve()))`
      - Files to fix: `jarvis.py`, `lib/ollama_client.py`, `services/coding_agent.py`, `services/self_healer.py`, `pipelines/agent_loop.py`, `lib/episodic_memory.py`, `lib/knowledge_manager.py`
      - Add `export JARVIS_ROOT=~/NixOSenv/Jarvis` to NixOS environment in `jarvis.nix`
- [ ] **BUG-2**: Fix `command` variable shadow in `jarvis.py:main()`
      - Rename the three intermediate assignments: `raw_cmd`, `cmd_lower`, `cmd`
      - Ensure HIGH_RISK_INTENTS check uses the classified `intent`, not `cmd`
- [ ] **BUG-3**: Fix `AgentLoop.run()` iteration guard
      - Change: `for i, step in enumerate(plan):`
      - To:     `for i, step in enumerate(plan[:max_iterations]):`
- [ ] **BUG-4**: Inject working memory into regular CLI chat
      - Load last 5 entries from `logs/history.jsonl`
      - Prepend as system context in `ollama_client.chat()` for `chat` alias
- [ ] **CLEANUP**: Update `Makefile` — fix hardcoded `.venv` path, add `JARVIS_ROOT` var
- [ ] **TEST**: `make test-all` must pass after all fixes

---

### 🟠 PHASE 1 — Budget Controller (Priority: CRITICAL · Est: 1 week)

> **Build this before adding any cloud API key. It is the safety gate.**

#### 1.1 — `config/budget.toml`

- [ ] Create `config/budget.toml` with this exact content:

```toml
[limits]
daily_tokens      = 200_000   # hard daily input+output token ceiling
daily_cost_usd    = 2.00      # hard daily cost ceiling (USD)
monthly_cost_usd  = 30.00     # hard monthly ceiling (USD)
warning_threshold = 0.80      # warn user at 80% daily usage

[per_task_limits]
research = 8_000
fix      = 12_000
reason   = 16_000
chat     = 6_000
default  = 4_000

[agent_loop]
max_steps             = 8
max_tokens_per_session = 40_000

[model_costs]
# cost per 1000 tokens in USD (input / output)
"claude-sonnet-4-5"  = { input = 0.003, output = 0.015 }
"claude-opus-4-5"    = { input = 0.015, output = 0.075 }
"gpt-4o"             = { input = 0.005, output = 0.015 }
```

#### 1.2 — `lib/budget_controller.py`

- [ ] Create `lib/budget_controller.py` implementing:

```python
# Public interface (implement exactly this)
class BudgetController:
    def check_and_reserve(self, task: str, estimated_tokens: int) -> BudgetDecision:
        """
        Returns BudgetDecision(allowed=bool, reason=str, fallback=str).
        Checks: (1) daily token limit, (2) per-task limit, (3) monthly cost.
        MUST be called before every cloud API request.
        """

    def record_usage(self, model: str, task: str,
                     prompt_tokens: int, output_tokens: int,
                     session_id: Optional[str] = None) -> None:
        """Writes to data/api_usage.db. Calculates cost from budget.toml rates."""

    def estimate_tokens(self, text: str) -> int:
        """Fast pre-flight estimate: len(text) // 4. No model call needed."""

    def get_daily_summary(self) -> dict:
        """Returns {tokens_used, tokens_remaining, cost_usd, requests_count}"""

    def start_session(self, session_id: str) -> None:
        """Register a new agent loop session for tracking."""

    def check_session_tokens(self, session_id: str) -> BudgetDecision:
        """Check if this session has exceeded max_tokens_per_session."""

    def end_session(self, session_id: str) -> None:
        """Finalize session, persist totals to events.db."""

    def is_local_only_mode(self) -> bool:
        """True if daily limit is exhausted → caller must use local models."""
```

- [ ] SQLite schema for `data/api_usage.db`:

```sql
CREATE TABLE IF NOT EXISTS api_usage (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            TEXT NOT NULL,
    model         TEXT NOT NULL,
    task          TEXT NOT NULL,
    prompt_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cost_usd      REAL NOT NULL,
    session_id    TEXT
);
CREATE INDEX idx_ts ON api_usage(ts);
CREATE INDEX idx_session ON api_usage(session_id);

CREATE TABLE IF NOT EXISTS sessions (
    session_id    TEXT PRIMARY KEY,
    started_at    TEXT NOT NULL,
    ended_at      TEXT,
    total_tokens  INTEGER DEFAULT 0,
    total_cost    REAL DEFAULT 0.0,
    status        TEXT DEFAULT 'active'
);
```

#### 1.3 — Integration

- [ ] Add `--budget-status` command to `jarvis.py` that calls `BudgetController.get_daily_summary()`
- [ ] Add budget warning line to `jarvis status` output
- [ ] Add budget panel to Rust TUI (`jarvis-monitor`) reading `api_usage.db`
- [ ] Emit budget events to `event_bus` when limits are hit

#### 1.4 — Tests

- [ ] `make test-budget` → test `check_and_reserve` blocks correctly at limits
- [ ] `make test-budget-session` → test session token tracking
- [ ] All tests pass with `make test-all`

---

### 🟡 PHASE 2 — Cloud LLM Integration (Priority: HIGH · Est: 1 week)

> **BudgetController (Phase 1) MUST be complete before starting this phase.**

#### 2.1 — `lib/cloud_client.py` (via OpenRouter)

- [ ] Create `lib/cloud_client.py` wrapping the OpenRouter API for unified access:

```python
# Public interface
class CloudClient:
    def chat(self, messages: list[dict], model: str = "anthropic/claude-sonnet-4-5",
             task: str = "chat", system: Optional[str] = None,
             max_tokens: int = 2048, stream: bool = False) -> str | Generator:
        """
        1. Call budget.check_and_reserve(task, estimated_tokens) — ABORT if denied.
        2. Call OpenRouter API (base_url="https://openrouter.ai/api/v1").
        3. Call budget.record_usage() with actual token counts from response.
        4. Emit event to event_bus.
        5. Return response text.
        """

    def is_available(self) -> bool:
        """True if OPENROUTER_API_KEY is set AND budget allows cloud calls."""
```

- [ ] OPENROUTER_API_KEY loaded from `config/.env` via `env_manager.py` — never hardcoded
- [ ] Add `OPENROUTER_API_KEY` to `REQUIRED_VARS` in `env_manager.py` (optional, no default)

#### 2.2 — Codebase Privacy Management

- [ ] Create `config/codebases.toml` to explicitly track and mark codebases by privacy tier:
```toml
# config/codebases.toml
[codebases]
# format: "absolute_path" = "privacy_tier"
"/home/qwerty/NixOSenv/Jarvis" = "private"
"/home/qwerty/projects/open_source_repo" = "public"
"/THE_VAULT/internal_docs" = "internal"
```
- [ ] Add `jarvis codebases` command to `jarvis.py`
      - Displays a holistic view of all tracked codebases and their explicitly marked privacy tier.
      - Includes commands to add/remove/modify codebase tracking: `jarvis codebases add <path> <tier>`

#### 2.3 — `lib/model_router.py` (v2 — complete replacement)

- [ ] Replace `model_router.py` with the v2 router implementing privacy tiers:

```python
from enum import Enum
from dataclasses import dataclass

class Privacy(Enum):
    PRIVATE  = 'private'   # personal data, local files → LOCAL ONLY, no exceptions
    INTERNAL = 'internal'  # generic content, prefer local
    PUBLIC   = 'public'    # safe to route to cloud

@dataclass
class RouteDecision:
    backend: str        # 'local' or 'cloud'
    model_alias: str    # key in models.toml OR cloud model name
    reasoning: str      # human-readable explanation for logs

# Task routing rules (task → default backend + alias)
TASK_RULES = {
    'complete':  ('local', 'fast'),    # ALWAYS local — latency + privacy
    'classify':  ('local', 'fast'),    # ALWAYS local — privacy sensitive
    'embed':     ('local', 'embed'),   # ALWAYS local
    'clean':     ('local', 'chat'),
    'summarize': ('local', 'chat'),
    'chat':      ('local', 'chat'),
    'fix':       ('local', 'coder'),   # local first, escalate if needed
    'diagnose':  ('local', 'coder'),
    'reason':    ('local', 'reason'),  # escalate if context > 16K
    'research':  ('local', 'chat'),    # public content — cloud allowed
}

def route(task: str,
          privacy: Privacy = Privacy.INTERNAL,
          context_tokens: int = 0,
          thinking: bool = False,
          budget_ok: bool = True) -> RouteDecision:
    """
    Priority order:
    1. Check `config/codebases.toml` for path match → if PRIVATE → always local, no cloud regardless of any other flag.
    2. Privacy.PRIVATE → always local, no cloud regardless of any other flag
    3. thinking=True   → local:reason (Qwen3 /think mode)
    4. context > 16K + PUBLIC + budget_ok → cloud (e.g., google/gemini-2.5-flash via OpenRouter)
    5. budget exhausted → force local with best available model
    6. Default task rule
    """
```

#### 2.4 — `lib/llm.py` (unified interface)

- [ ] Create `lib/llm.py` as the single entry point for all LLM calls:

```python
# Public interface — replaces direct calls to ollama_client / cloud_client
def ask(prompt: str,
        task: str = 'chat',
        privacy: Privacy = Privacy.INTERNAL,
        context_tokens: int = 0,
        thinking: bool = False,
        system: Optional[str] = None,
        messages: Optional[list] = None,
        stream: bool = False) -> str | Generator:
    """
    1. Call model_router.route() to get RouteDecision.
    2. Dispatch to OllamaClient (local) or CloudClient (cloud).
    3. Log the call to event_bus.
    4. Return response.
    """
```

#### 2.5 — Migration

- [ ] Update `pipelines/research_agent.py` to use `llm.ask()` with `Privacy.PUBLIC` (Safe to route to Gemini 2.5/Grok via OpenRouter)
- [ ] Update `pipelines/agent_loop.py` to use `llm.ask()` with `Privacy.INTERNAL` (Safe to route to Claude Sonnet via OpenRouter)
- [ ] Update `services/coding_agent.py` to use `llm.ask()` with `Privacy.PRIVATE` (Strictly local qwen3:14b)
- [ ] Update `services/daily_digest.py` and background tasks to use `llm.ask()` with Mistral Experiment tier if appropriate.
- [ ] Do NOT migrate autocomplete (FIM) — it stays on OllamaClient directly

#### 2.6 — Tests

- [ ] `make test-router` → test all routing rules including privacy override
- [ ] `make test-cloud` → test cloud client (mock Anthropic API, no real calls)
- [ ] `make test-llm` → test unified interface dispatch

---

### 🟡 PHASE 3 — Conversation Memory (Priority: HIGH · Est: 3-4 days)

#### 3.1 — `lib/working_memory.py`

- [ ] Create `lib/working_memory.py`:

```python
# Public interface
class WorkingMemory:
    """Persists conversation turns across CLI sessions in data/sessions.db."""

    def load_session(self, session_id: Optional[str] = None) -> list[dict]:
        """Load last N turns for the session. If no session_id, use today's."""

    def save_turn(self, role: str, content: str,
                  session_id: Optional[str] = None) -> None:
        """Append a single turn (user or assistant) to the session."""

    def get_context_messages(self, max_turns: int = 10) -> list[dict]:
        """Return last max_turns as [{'role': ..., 'content': ...}] for injection."""

    def summarize_and_compress(self) -> None:
        """If session > 6000 tokens, summarize old turns, keep last 4 verbatim."""

    def new_session(self) -> str:
        """Start a fresh session, return new session_id."""

    def clear(self) -> None:
        """Delete current session's turns (for 'jarvis forget' command)."""
```

- [ ] SQLite schema in `data/sessions.db`:

```sql
CREATE TABLE IF NOT EXISTS turns (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    ts         TEXT NOT NULL,
    role       TEXT NOT NULL,   -- 'user' | 'assistant' | 'system'
    content    TEXT NOT NULL,
    tokens     INTEGER          -- estimated token count
);
CREATE INDEX idx_session_ts ON turns(session_id, ts);
```

#### 3.2 — Integration

- [ ] Inject `WorkingMemory.get_context_messages()` into ALL `llm.ask()` calls
- [ ] Add `jarvis forget` command to `jarvis.py` → calls `working_memory.clear()`
- [ ] Add `jarvis sessions` command → lists recent sessions with token/turn counts
- [ ] Session ID = date string (e.g., `2026-03-07`) for natural daily grouping

#### 3.3 — Tests

- [ ] `make test-memory` → test persistence across simulated sessions

---

### 🟡 PHASE 4 — Tool Execution + ReAct Agent (Priority: HIGH · Est: 2 weeks)

#### 4.1 — `lib/tools.py`

- [ ] Create `lib/tools.py` with the tool registry:

```python
@dataclass
class Tool:
    name:             str
    description:      str
    parameters:       dict         # JSON Schema for the tool's args
    privacy:          Privacy      # affects routing of the tool's output
    timeout_s:        int = 30
    requires_confirm: bool = False  # prompt user before executing

# Implement these tools:
TOOL_REGISTRY = {
    'shell_run':   Tool(..., Privacy.PRIVATE, timeout_s=10, requires_confirm=True),
    'file_read':   Tool(..., Privacy.PRIVATE, timeout_s=5,  requires_confirm=False),
    'file_write':  Tool(..., Privacy.PRIVATE, timeout_s=5,  requires_confirm=True),
    'file_patch':  Tool(..., Privacy.PRIVATE, timeout_s=5,  requires_confirm=True),
    'web_search':  Tool(..., Privacy.PUBLIC,  timeout_s=15, requires_confirm=False),
    'web_fetch':   Tool(..., Privacy.PUBLIC,  timeout_s=20, requires_confirm=False),
    'python_eval': Tool(..., Privacy.PRIVATE, timeout_s=10, requires_confirm=False),
    'git_commit':  Tool(..., Privacy.PRIVATE, timeout_s=10, requires_confirm=True),
    'git_status':  Tool(..., Privacy.PRIVATE, timeout_s=5,  requires_confirm=False),
}

def execute(tool_name: str, args: dict) -> ToolResult:
    """
    Execute a tool safely:
    1. Look up tool in TOOL_REGISTRY — raise if not found.
    2. If requires_confirm: prompt user, abort if declined.
    3. Run with timeout enforcement.
    4. Return ToolResult(success, output, error).
    5. Emit event to event_bus.
    """
```

**SAFETY RULES for tool executor:**
- `shell_run`: Never use `shell=True`. Always list form. Capture stdout+stderr.
- `file_write` and `file_patch`: Git commit the file BEFORE modifying it.
- `python_eval`: Use RestrictedPython or subprocess sandbox — never `eval()` directly.
- All tools: enforce `timeout_s`. Kill the subprocess if exceeded.

#### 4.2 — ReAct Agent Loop (upgrade `pipelines/agent_loop.py`)

- [ ] Replace the plan→execute loop with a ReAct (Reason + Act) pattern:

```python
def run_react(self, user_prompt: str, max_steps: int = 8) -> str:
    """
    Each step:
      Thought: model reasons about what to do next
      Action:  model selects a tool + args (structured JSON output)
      Observation: tool executes, result added to history
    Loop ends when model outputs FINAL_ANSWER or max_steps reached.
    """
    budget = BudgetController()
    session_id = budget.start_session(str(uuid4()))

    history = []
    for step in range(max_steps):
        # 1. Budget check before each step
        decision = budget.check_session_tokens(session_id)
        if not decision.allowed:
            return f"[Aborted: {decision.reason}] Partial: {history[-1]['obs'] if history else 'No progress'}"

        # 2. Get model's next action
        action = self._get_next_action(history, TOOL_REGISTRY, user_prompt)

        # 3. Detect final answer
        if action.type == 'FINAL_ANSWER':
            budget.end_session(session_id)
            return action.content

        # 4. Execute tool
        observation = tool_executor.execute(action.tool, action.args)

        # 5. Log step
        history.append({'step': step, 'thought': action.thought,
                        'tool': action.tool, 'args': action.args,
                        'obs': str(observation)})
        emit('agent_loop', 'step_complete', {'step': step, 'tool': action.tool})

    budget.end_session(session_id)
    return f"[Max steps reached] Best result: {history[-1]['obs']}"
```

#### 4.3 — Tests

- [ ] `make test-tools` → test each tool with mock inputs (no real shell execution)
- [ ] `make test-react` → test ReAct loop with mock model responses
- [ ] Integration test: `jarvis 'what files did I modify in the last git commit'`
      Expected: agent uses `git_status` tool and returns accurate output

---

### 🔵 PHASE 5 — sqlite-vec Vector Upgrade (Priority: MEDIUM · Est: 3 days)

#### 5.1 — Install sqlite-vec

- [ ] Add `sqlite-vec` to NixOS flake dependencies OR install via pip:
  ```bash
  pip install sqlite-vec
  ```
- [ ] Verify: `python -c "import sqlite_vec; print(sqlite_vec.version())"`

#### 5.2 — `lib/semantic_memory.py`

- [ ] Create `lib/semantic_memory.py` replacing the raw BLOB approach in `knowledge_manager.py`:

```python
# Public interface
class SemanticMemory:
    """sqlite-vec powered vector store. Drop-in upgrade to existing knowledge.db."""

    def ingest(self, content: str, metadata: dict,
               layer: int = 1, category: str = None) -> None:
        """Chunk → embed → store in sqlite-vec virtual table."""

    def query(self, query_text: str, k: int = 5,
              category: Optional[str] = None,
              use_hybrid: bool = True) -> list[SearchResult]:
        """
        BM25 + vector RRF hybrid retrieval.
        Returns top-k chunks with scores.
        Preserves the existing coding_agent.py RRF logic.
        """

    def migrate_from_blob(self) -> None:
        """One-time migration of existing BLOB embeddings to sqlite-vec."""
```

- [ ] sqlite-vec schema:

```sql
-- After: import sqlite_vec; db.enable_load_extension(True); sqlite_vec.load(db)
CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0(
    embedding float[768]   -- nomic-embed-text dimension
);

CREATE TABLE IF NOT EXISTS chunk_metadata (
    rowid    INTEGER PRIMARY KEY,  -- links to vec_chunks rowid
    layer    INTEGER NOT NULL,
    category TEXT,
    source   TEXT,
    content  TEXT NOT NULL,
    ts       TEXT NOT NULL
);
```

#### 5.3 — Migration & Tests

- [ ] `make migrate-vectors` → runs `SemanticMemory.migrate_from_blob()` on existing `knowledge.db`
- [ ] `make test-semantic` → test ingest + query on 10 sample documents
- [ ] Benchmark: query latency before vs after migration (log to events.db)

---

### 🔵 PHASE 6 — Knowledge Graph + mem0 Memory (Priority: MEDIUM · Est: 2-3 weeks)

- [ ] Evaluate `mem0` library for production memory management
      - Install: `pip install mem0ai`
      - Test: replace `lib/episodic_memory.py` with mem0 backend
      - Decision criterion: if mem0 adds < 50MB RAM overhead → adopt
- [ ] Add entity extraction to ingest pipeline using qwen3:1.7b
      - Extract: (subject, relation, object) triples from each chunk
      - Store in `knowledge.db` as `entities` table
- [ ] Build `lib/knowledge_graph.py` using networkx (in-process, no new service)
- [ ] Add `jarvis what do I know about <topic>` → traverse knowledge graph + RAG
- [ ] Upgrade `services/daily_digest.py` to use episodic + semantic + graph memory

---

### ⚪ PHASE 7 — Autonomous Capabilities (Priority: LOW · Ongoing)

- [ ] Enable self-improvement loop to use tool calls (currently text-only)
      - Self-edits must: git commit before, apply as patch, run tests, revert if tests fail
- [ ] Add proactive monitoring: detect workflow patterns, suggest Jarvis improvements
- [ ] Add voice I/O via `whisper.cpp` (CPU-only, ~1GB, add to NixOS flake)
- [ ] Build web UI: FastAPI + HTMX, served on localhost:8080
- [ ] Add calendar/task integration (local files, not cloud service)
- [ ] Add `jarvis plan <goal>` → multi-day task planning with persistence

---

## 5. Key Technical Decisions (Immutable)

| Decision | Reasoning |
|---|---|
| `JARVIS_ROOT` env var | Never hardcode paths — portability across machines/users |
| `mineru[pipeline]` NOT `[all]` | No GPU. `[all]` pulls CUDA deps that fail to build on NixOS |
| Home Manager for LSPs, NOT mason.nvim | mason downloads ELF binaries referencing `/lib/ld-linux.so` — broken on NixOS |
| `keep_alive: "0"` for background models | Frees 5GB RAM immediately. Non-negotiable on 16GB |
| `keep_alive: "5m"` for qwen3:14b during coding | 30s cold start is too slow for interactive use |
| Ollama concurrency lock removed | Removed — Ollama's internal scheduler handles this now |
| `subprocess` always list form + `timeout=` | Never `shell=True` with model output — injection risk |
| `systemctl --user` for service lifecycle | NOT `subprocess.Popen` — prevents zombie processes |
| `plenary.curl` async in Lua | NEVER `vim.fn.system()` — freezes Neovim for 30-90s |
| Delete `local-ai.nix` | References CUDA packages — broken on Intel Iris Xe |
| `BudgetController.check_and_reserve()` before ALL cloud calls | Safety gate — no exceptions |
| Git commit before any file mutation by agent | Enables instant rollback of self-modifications |
| `Privacy.PRIVATE` → local only, no override | Privacy is structural, enforced in router code |
| `sqlite-vec` over ChromaDB/Qdrant | No new services — extends existing SQLite setup |

---

## 6. Model Reference

| Model | Alias | RAM | Speed | keep_alive | Use For |
|---|---|---|---|---|---|
| `qwen3:1.7b-q4_K_M` | `fast`, `complete` | 1.3GB | 30-45 tok/s | `"10m"` | Intent classify, FIM autocomplete |
| `qwen3:8b-q4_K_M` | `chat` | 5.5GB | 8-12 tok/s | `"5m"` | General chat, RAG Q&A, cleaning |
| `qwen2.5-coder:7b-instruct` | `coder` | 5.2GB | 9-13 tok/s | `"5m"` | Code gen, debugging, inline fixes |
| `qwen3:14b-q4_K_M` | `reason` | 9.5GB | 3-5 tok/s | `"5m"` active / `"0"` idle | Complex planning, NixOS generation |
| `nomic-embed-text` | `embed` | 0.3GB | instant | always | Vector embeddings |
| `claude-sonnet-4-5` | — (cloud) | — | — | — | Long context, frontier coding (via OpenRouter) |
| `gemini-2.5-flash` | — (cloud) | — | — | — | Long-context research, summarization (via OpenRouter) |
| `grok-4.1-fast` | — (cloud) | — | — | — | Extremely long context, public research (via OpenRouter) |

---

## 7. Component Spec Reference

### SPEC: `lib/budget_controller.py` (Phase 1)

**File**: `lib/budget_controller.py`
**Dependencies**: `config/budget.toml`, `data/api_usage.db` (auto-created)
**Public interface**: See Phase 1.2 above.

**Acceptance Criteria:**
1. `check_and_reserve('research', 9000)` returns `allowed=False` (exceeds per_task_limits.research=8000)
2. After simulating 201K tokens in one day → `check_and_reserve` returns `allowed=False, reason='daily_limit'`
3. `is_local_only_mode()` returns `True` when daily tokens exhausted
4. `record_usage` writes a row to `api_usage.db` with correct cost calculation
5. `get_daily_summary()` returns accurate aggregates from `api_usage.db`

**Agent Prompt** (paste this to implement Phase 1.2):
```
Implement lib/budget_controller.py for the Jarvis project.

Context:
- JARVIS_ROOT = Path(os.environ.get("JARVIS_ROOT", Path(__file__).parent.parent.resolve()))
- Config loaded from: JARVIS_ROOT / "config" / "budget.toml"
- Database: JARVIS_ROOT / "data" / "api_usage.db" (create if not exists)
- Import event_bus.emit() for logging budget events
- Use tomllib (Python 3.11+) or tomli for TOML parsing

Implement the full BudgetController class with the exact public interface
specified in docs/BOOTSTRAP.md Section 7, SPEC: budget_controller.py.

After implementing:
1. Write a __main__ block that runs all 5 acceptance criteria as assertions
2. Add `make test-budget` target to Makefile
3. Run make test-budget and confirm all assertions pass
4. Commit: "feat(phase-1): implement BudgetController"
```

---

### SPEC: `lib/cloud_client.py` (Phase 2)

**File**: `lib/cloud_client.py`
**Dependencies**: `anthropic` SDK, `lib/budget_controller.py`, `lib/env_manager.py`
**Install**: `pip install anthropic` (add to `Makefile` setup target)

**Acceptance Criteria:**
1. `is_available()` returns `False` when `ANTHROPIC_API_KEY` not set
2. `chat()` raises `BudgetExceededError` when `budget.is_local_only_mode()` is True
3. `chat()` calls `budget.record_usage()` with actual token counts after successful call
4. All API calls go through `budget.check_and_reserve()` first — no exceptions

**Agent Prompt** (paste this to implement Phase 2.1):
```
Implement lib/cloud_client.py for the Jarvis project.

Context:
- Install: anthropic Python SDK
- API key: loaded via lib/env_manager.py, key name: ANTHROPIC_API_KEY
- Budget gate: call BudgetController().check_and_reserve() BEFORE every API call
- Use model "claude-sonnet-4-5" as default
- Emit events to lib/event_bus.emit('cloud_client', 'request_completed', {...})
- NEVER hardcode the API key

Implement CloudClient with the exact public interface in docs/BOOTSTRAP.md
Section 7, SPEC: cloud_client.py.

After implementing:
1. Mock the Anthropic API to test without real calls
2. Run all 4 acceptance criteria
3. Commit: "feat(phase-2): implement CloudClient"
```

---

### SPEC: `lib/tools.py` (Phase 4)

**File**: `lib/tools.py`
**Dependencies**: `lib/event_bus.py`, `RestrictedPython` (or subprocess sandbox)

**Acceptance Criteria:**
1. `execute('shell_run', {'cmd': 'echo hello'})` returns `ToolResult(success=True, output='hello\n')`
2. `execute('shell_run', {'cmd': 'sleep 100'})` raises `ToolTimeoutError` after `timeout_s`
3. `execute('file_write', {...})` creates a git commit of the file BEFORE writing
4. `execute('unknown_tool', {})` raises `ToolNotFoundError`
5. Any tool with `requires_confirm=True` prompts user before executing

**Agent Prompt** (paste this to implement Phase 4.1):
```
Implement lib/tools.py for the Jarvis project.

Context:
- All subprocess calls: list form, never shell=True, enforce timeout_s
- file_write and file_patch: git commit the target file BEFORE modifying
  (use: git add <file> && git commit -m "pre-agent backup: <file>")
- python_eval: use subprocess with a fresh Python process (never eval() directly)
- web_search: call SearXNG at localhost:8888/search?q=<query>&format=json
- Emit tool execution events to lib/event_bus
- Privacy field on Tool affects how results are routed in the agent

Implement TOOL_REGISTRY and execute() with the exact spec in
docs/BOOTSTRAP.md Section 7, SPEC: tools.py.

After implementing:
1. Write __main__ test block for all 5 acceptance criteria (mock filesystem)
2. Add make test-tools to Makefile
3. Commit: "feat(phase-4): implement ToolRegistry and executor"
```

---

## 8. How to Resume After Quota Exhaustion

1. Run: `cat docs/BOOTSTRAP.md` — orient completely
2. Run: `make test-all` — verify current system health
3. Run: `make status` — check service states
4. Find the first `[ ]` in Section 4 — that is your task
5. Read its SPEC in Section 7
6. Copy its **Agent Prompt** and paste into your coding agent
7. Implement → test → mark `[x]` → commit → next item

---

## 9. Architecture Diagram (Text)

```
┌─────────────────── INTERACTION LAYER ───────────────────────┐
│   CLI (jarvis.py)  │  Neovim Plugin (lua/)  │  TUI (Rust)   │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────── ORCHESTRATION LAYER ────────────────────┐
│  IntentClassifier  │  AgentLoop (ReAct)  │  BudgetController │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌─────────────────── MODEL ROUTING LAYER ─────────────────────┐
│           ModelRouter v2 (task + privacy + cost + context)   │
└───────────────────┬─────────────────────────┬───────────────┘
                    │                         │
        ┌───────────▼──────────┐   ┌─────────▼──────────────┐
        │  Ollama (local)      │   │  Anthropic API (cloud)  │
        │  qwen3:1.7b / 8b /  │   │  claude-sonnet-4-5      │
        │  14b / coder / embed │   │  (budget-gated)         │
        └───────────┬──────────┘   └─────────┬──────────────┘
                    └────────────┬────────────┘
                                 │
┌──────────────────── MEMORY LAYER ───────────────────────────┐
│  WorkingMemory (sessions.db)  │  EpisodicMemory (events.db) │
│  SemanticMemory (sqlite-vec)  │  KnowledgeGraph (networkx)  │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌─────────────────── TOOL + ENVIRONMENT LAYER ────────────────┐
│  shell_run │ file_read/write │ web_search │ python_eval │ git │
│  SearXNG   │ systemd services │ Ollama daemon │ event_bus    │
└─────────────────────────────────────────────────────────────┘
```

---

*Last updated: 2026-03-07. Phase 8 COMPLETE. Phase 9 (Refinement & Stress Testing) in progress.*

## Phase 9: Final Refinement & Stress Testing (User Req: 2026-03-07)
The following requests are documented for active tracking:
- [ ] **Privacy Update**: Explicitly toggle off private options for NixOS, Neovim, and Jarvis core (all public).
- [ ] **Stress Test**: Perform rigorous "Bash Language Learning" (Research -> Ingest -> Layer 3).
- [ ] **Model Management**: Add Jarvis capabilities to manage/monitor currently used models and API keys.
- [ ] **Voice Toggle**: Add ability to toggle voice commands and preference suggestions.
- [ ] **Documentation Overhaul**: 
    - Update project spec, system architecture (UML).
    - Remove/Update outdated bootstrap sections.
    - Update all component usage docs.
    - Update man pages, README.md, INSTALL.md.
- [ ] **Scripting**: Update backup and archiving scripts.
- [ ] **Final Sync**: Commit and push all changes.

*Architecture review by Senior AI Systems Architect — see jarvis_architecture_report.docx*
