Prompt for Antigravity Coding Agent:

---

# Jarvis AI Orchestrator: Comprehensive Enhancement Specification

You are an expert systems architect and senior engineer embedded in the Jarvis project — a NixOS-based AI orchestrator written primarily in Python (82%), Rust (6%), Lua (7%), and Shell (2%). Your task is to produce detailed, production-ready code implementations, ASCII/Mermaid architectural diagrams, and step-by-step integration plans for three major subsystem upgrades: the External Reasoning System (ERS), the Indexing/RAG pipeline, and the ModelRouter. All output must be grounded in the existing codebase structure (`lib/ers/`, `lib/models/`, `services/jarvis_lsp.py`, Vault storage), respect the NixOS/Neovim ecosystem exclusively, and maintain an offline-first, privacy-preserving design philosophy. No Windows support. No VS Code. No cloud dependencies that cannot be toggled off via a single config flag.

Read every constraint carefully before generating any code. Violating ecosystem constraints is a critical failure.

---

## SECTION 1 — Problem Analysis

Begin by producing a structured problem analysis for each of the three subsystems. For each, enumerate:

1. **Current Limitations** — What architectural or functional gaps exist? Be specific: e.g., "ERS currently executes YAML chains sequentially with no failure recovery path," or "Indexing uses naive keyword search with no vector similarity layer." Reference the existing file structure (`lib/ers/chain.py`, `lib/ers/executor.py`, `lib/models/router.py`, etc.) as if you have read and internalized them.

2. **Impact on User Capability** — How do these gaps degrade the experience of a developer using Jarvis for AI-assisted programming, reasoning over codebases, or multi-step agentic tasks? Tie each gap to a concrete use-case failure (e.g., "A chain that calls a failing tool causes the entire reasoning session to abort with no retry, losing all intermediate context").

3. **Opportunity Space** — What becomes possible once each subsystem is upgraded? Include at least three concrete scenarios per subsystem: one involving pure local operation (Ollama only), one involving hybrid cloud fallback, and one involving a multi-modal or cross-system integration.

This analysis section should be approximately 400 words minimum. Do not skip it — it frames all downstream architectural decisions.

---

## SECTION 2 — Proposed Architecture

Produce a full architectural overview using **both** an ASCII diagram and a Mermaid diagram. The Mermaid diagram should be renderable in a standard Mermaid-compatible viewer (use `graph TD` or `sequenceDiagram` as appropriate). The ASCII diagram should be terminal-friendly (80-column max width).

The architecture must show:

- The new ERS subsystem with: `ChainExecutor` → `AdaptiveRouter` → `ToolRegistry` → `SelfCorrectionLoop` → `MetricsCollector`
- The new Indexing pipeline with: `IngestionWorker` (multi-modal) → `EmbeddingEngine` (local FAISS + SentenceTransformers via Ollama) → `SemanticSearchIndex` → `ASTParser` (for code) → `AutoReindexTimer`
- The new ModelRouter with: `HybridRouter` → `CostAwareSelector` → `PromptRefiner` → `SecureAPIHandler` → `LocalFallbackPool`
- All inter-system connections: how ERS invokes the ModelRouter, how ERS queries the Index, how the Index feeds context into PromptRefiner, and how MetricsCollector feeds back into AdaptiveRouter
- Vault storage as the secure secret/state backend, connected to SecureAPIHandler and ChainExecutor state persistence
- The Neovim plugin layer (`jarvis_lsp.py` and Lua plugin interface) as the user-facing surface consuming all three subsystems

Label every node. Include data-flow direction arrows. Show async boundaries with a visual marker (e.g., `~~async~~` in Mermaid or `[ASYNC]` in ASCII).

---

## SECTION 3 — ERS Enhancement: Code Implementation

Produce complete, runnable Python implementations for the following ERS components. Each file should include full imports, type hints, docstrings, and inline comments explaining non-obvious logic. Do not produce stubs — produce real implementations.

### 3.1 — `lib/ers/adaptive_router.py`

Implement `AdaptiveRouter` — a class that wraps chain execution and dynamically reroutes on failure. Requirements:

- Accept a `ChainDefinition` (YAML-parsed dataclass) and a `ToolRegistry`
- Maintain a `retries: int` and `backoff_strategy: Literal["linear", "exponential", "jitter"]` per step
- On tool failure, attempt: (1) retry with same tool, (2) substitute with semantically equivalent tool from registry, (3) escalate to `SelfCorrectionLoop`, (4) mark step as `DEGRADED` and continue chain if `allow_partial: true` is set in the YAML
- Emit structured log events to `MetricsCollector` at each decision point
- Be fully async (`asyncio`-based)

### 3.2 — `lib/ers/parallel_executor.py`

Implement `ParallelExecutor` — extends the existing sequential executor to support parallel step groups. Requirements:

- YAML chain steps can be tagged with `parallel_group: <group_id>` — all steps sharing a group_id execute concurrently via `asyncio.gather`
- Steps without a group_id execute sequentially in declared order
- Shared state between parallel steps is managed via a thread-safe `ChainContext` object (implement this too, using `asyncio.Lock`)
- Timeout per step group configurable via `timeout_seconds` in YAML
- On partial group failure, behavior is governed by `group_failure_policy: [abort | continue | retry_failed]`

### 3.3 — `lib/ers/self_correction.py`

Implement `SelfCorrectionLoop` — an LLM-driven self-correction mechanism. Requirements:

- Takes a failed step's: input, output, error message, and the original chain intent
- Constructs a meta-prompt instructing the ModelRouter to diagnose the failure and produce a corrected tool call or revised input
- Runs up to `max_correction_attempts: int` (default 3) correction cycles
- Each correction attempt is scored by a `CorrectionScorer` (implement a simple heuristic scorer based on: error type match, output format validity, semantic similarity to expected output using local embeddings)
- If correction succeeds, injects corrected output back into `ChainContext` and resumes
- Logs all correction attempts to MetricsCollector with full before/after diffs

### 3.4 — `lib/ers/yaml_schema.py`

Define the enhanced YAML chain schema as a set of Pydantic v2 models. The schema must support:

- `steps[]` with fields: `id`, `tool`, `inputs`, `outputs`, `parallel_group`, `timeout_seconds`, `allow_partial`, `on_failure: [retry | substitute | correct | skip | abort]`
- `conditionals[]`: list of `{condition: "<jinja2 expression>", jump_to: "<step_id>"}` — evaluated after each step using the current `ChainContext` as the Jinja2 rendering context
- `tool_chain[]`: shorthand for declaring a linear sequence of tools where output of step N is automatically piped to input of step N+1
- `external_apis[]`: list of named API integrations with `{name, endpoint, auth_env_var, rate_limit_rpm, timeout_seconds}`
- `metrics`: block with `{collect: bool, export_to: [stdout | file | prometheus], benchmark_suite: str}`

Provide three complete example YAML chains demonstrating: (a) a sequential code-analysis chain with conditional branching based on language detection, (b) a parallel web-research + local-index query chain that merges results, (c) a self-correcting chain for LLM-based test generation that loops until tests pass.

### 3.5 — `lib/ers/metrics_collector.py`

Implement `MetricsCollector` — an honest benchmark harness. Requirements:

- Track per-step: latency (ms), token usage (input/output), tool success/failure rate, correction attempt count, final status
- Track per-chain: total latency, total cost estimate (using a `CostModel` dataclass with per-token rates per model), success rate, degradation rate
- Expose a `generate_report(format: Literal["json", "markdown", "prometheus"])` method
- Integrate with the existing benchmark suite — produce a `BenchmarkRunner` that can replay stored chains from a `fixtures/` directory and compare metrics across runs (delta reporting)
- Store all metrics in a local SQLite database (`~/.jarvis/metrics.db`) via `aiosqlite`
- Expose a simple HTTP endpoint (optional, toggled via config) using `aiohttp` for Prometheus scraping

---

## SECTION 4 — Indexing Enhancement: Code Implementation

### 4.1 — `lib/indexing/embedding_engine.py`

Implement `EmbeddingEngine` — a local-first embedding abstraction. Requirements:

- Primary backend: Ollama embeddings API (`http://localhost:11434/api/embeddings`) using the configured embedding model (default: `nomic-embed-text`)
- Secondary backend: `sentence-transformers` library as fallback if Ollama is unavailable
- Produce embeddings as `numpy` arrays, cached to disk via `joblib.Memory` with a configurable cache directory
- Batch embedding support: accept `List[str]`, return `np.ndarray` of shape `(N, embedding_dim)`
- Include a `similarity(a: np.ndarray, b: np.ndarray) -> float` utility using cosine similarity

### 4.2 — `lib/indexing/faiss_index.py`

Implement `FAISSIndex` — a persistent FAISS vector store. Requirements:

- Use `faiss-cpu` (no GPU dependency)
- Support `IndexFlatIP` (inner product / cosine) and `IndexIVFFlat` (approximate, for large corpora) — switchable via config
- Persist index to disk (`~/.jarvis/index/faiss.bin`) and metadata to a companion SQLite database (`~/.jarvis/index/meta.db`) mapping vector IDs to: source file path, chunk index, chunk text, chunk type (`code | doc | comment | docstring | image_caption`), last modified timestamp
- Expose: `add(chunks: List[Chunk])`, `search(query_embedding: np.ndarray, top_k: int) -> List[SearchResult]`, `delete_by_source(path: str)`, `rebuild()`, `stats() -> IndexStats`
- Thread-safe via `asyncio.Lock`

### 4.3 — `lib/indexing/ingestor.py`

Implement `IngestionWorker` — multi-modal document ingestion. Requirements:

- **Text/Markdown**: chunk by paragraph with configurable overlap (sliding window), strip front-matter
- **Python code**: use `ast` module to parse into function/class/module chunks — each chunk includes the AST node type, name, docstring, and full source. Produce a `SymbolGraph` (adjacency list) representing import dependencies and call relationships
- **Rust code**: use regex-based chunking on `fn`, `impl`, `struct`, `trait` boundaries (full AST parsing is optional, toggled via config with `tree-sitter` as the backend if enabled)
- **Lua code**: chunk by function definition using pattern matching
- **Images**: extract captions using Ollama's vision model if available (`llava` or `moondream`), store caption as the text representation
- **Jupyter notebooks**: extract cell-by-cell, preserving cell type (`code | markdown | output`)
- All chunks are normalized to a `Chunk` dataclass: `{id, source_path, chunk_type, text, metadata: dict, embedding: Optional[np.ndarray]}`

### 4.4 — `lib/indexing/auto_reindex.py`

Implement `AutoReindexTimer` — filesystem watcher + scheduled reindexing. Requirements:

- Use `watchdog` library to monitor configured directories for file changes
- Debounce rapid changes (configurable `debounce_seconds`, default 2.0)
- On change event: (1) delete old chunks for the modified file, (2) re-ingest and re-embed, (3) update FAISS index incrementally (no full rebuild unless `force_rebuild: true`)
- Scheduled full rebuild via `apscheduler` (configurable cron expression, default: daily at 3am)
- Expose a manual trigger: `POST /index/rebuild` on the optional internal HTTP API
- Log all reindex events to `~/.jarvis/index/reindex.log` with timestamps and chunk delta counts

### 4.5 — `lib/indexing/semantic_search.py`

Implement `SemanticSearch` — the query interface. Requirements:

- Accept natural language queries, embed them via `EmbeddingEngine`, search `FAISSIndex`
- Support hybrid search: combine vector similarity score with BM25 keyword score (implement a simple BM25 scorer over the metadata DB) — configurable weighting (`vector_weight`, `bm25_weight`)
- Support filtered search: filter by `chunk_type`, `source_path` prefix, or `last_modified` range
- Return `SearchResultSet` with: ranked `SearchResult` list, query embedding, search latency, index stats at query time
- Integrate with ERS: expose as a registered tool in `ToolRegistry` so chains can call `semantic_search(query, top_k, filters)` directly

---

## SECTION 5 — ModelRouter Enhancement: Code Implementation

### 5.1 — `lib/models/hybrid_router.py`

Implement `HybridRouter` — extends existing `router.py`. Requirements:

- **Routing logic**: score each available model against the task using: (1) task complexity estimate (token count + reasoning depth heuristic), (2) model capability profile (configurable per-model YAML profile with fields: `max_context`, `reasoning_score`, `code_score`, `cost_per_1k_tokens`, `latency_p50_ms`, `requires_network`), (3) current system load (CPU/RAM via `psutil`), (4) user-configured cost budget (`max_cost_per_request_usd`)
- **Local-first**: always prefer Ollama models. Only route to cloud (Claude via Anthropic API, OpenAI) if: local model score falls below `quality_threshold` AND cloud routing is enabled in config AND cost budget allows
- **Fallback chain**: `local_primary` → `local_secondary` → `cloud_primary` → `cloud_secondary` → `error`
- All routing decisions logged to MetricsCollector

### 5.2 — `lib/models/prompt_refiner.py`

Implement `PromptRefiner` — automatic prompt optimization. Requirements:

- Maintain a `PromptTemplate` registry (YAML-defined, stored in `~/.jarvis/prompts/`)
- For each incoming prompt: (1) classify task type (code generation, explanation, reasoning, search, correction), (2) select best template, (3) inject relevant context from SemanticSearch (top-3 chunks), (4) apply model-specific formatting (e.g., Claude prefers XML tags, Ollama models prefer plain markdown)
- Track prompt performance via MetricsCollector — if a prompt+model combination has a high correction rate, flag it for review and optionally auto-tune via few-shot example injection
- Support `dry_run` mode: return the refined prompt without sending it to any model

### 5.3 — `lib/models/secure_api_handler.py`

Implement `SecureAPIHandler` — secure cloud API integration. Requirements:

- Read API keys exclusively from environment variables (never config files) — `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` — with clear error if missing and cloud routing is enabled
- Integrate with HashiCorp Vault (via `hvac` library) as an alternative secret source, using the existing Vault storage infrastructure
- Rate limiting: token-bucket implementation per provider, configurable `rpm` and `tpm` limits, with backoff on 429 responses
- Request/response logging: log metadata only (model, token counts, latency, cost estimate) — never log prompt content unless `debug_log_prompts: true` is explicitly set
- Implement a `CostTracker` that accumulates spend per session and per day, writing to `~/.jarvis/costs.db`, and emits a warning when approaching configured budget limits

---

## SECTION 6 — Integration Plan

Produce a numbered, step-by-step integration plan for merging all of the above into the existing Jarvis codebase. Each step must include:

- **What** is being done
- **Which files** are created, modified, or deleted
- **Why** — the architectural rationale
- **Verification** — a specific test or observable behavior confirming the step succeeded
- **Rollback** — how to undo the step if it breaks something

The plan must cover at minimum: (1) adding new Python dependencies to the Nix flake (`flake.nix` — add `faiss-cpu`, `sentence-transformers`, `watchdog`, `apscheduler`, `aiosqlite`, `aiohttp`, `hvac`, `psutil`, `pydantic` v2 to the Python environment), (2) wiring the new `AutoReindexTimer` into the Jarvis service startup sequence, (3) registering `SemanticSearch` as an ERS tool in `ToolRegistry`, (4) updating `jarvis_lsp.py` to expose new capabilities (index query, chain status, metrics dashboard) as LSP commands consumable by the Neovim Lua plugin, (5) updating the Lua plugin (`plugin/jarvis.lua` or equivalent) to add keybindings for: trigger semantic search, view chain execution status, view metrics report, trigger manual reindex.

---

## SECTION 7 — Testing Plan

Produce a comprehensive testing plan covering:

- **Unit tests** for every new class — use `pytest` with `pytest-asyncio`. Provide at least 3 test cases per class covering: happy path, failure/edge case, and async concurrency behavior. Use `unittest.mock` and `pytest-mock` for external dependencies (Ollama API, cloud APIs, filesystem).
- **Integration tests** — define three end-to-end test scenarios that exercise the full stack (ERS → ModelRouter → Index → response): (1) a local-only code explanation task, (2) a hybrid routing task where the local model is intentionally degraded to force cloud fallback, (3) a full chain execution with parallel steps, self-correction, and metric export
- **Benchmark suite expansion** — extend the existing honest benchmark suite to include: ERS chain latency under load (10/50/100 concurrent chains), FAISS search latency as corpus size scales (1k/10k/100k chunks), ModelRouter routing decision latency, embedding throughput (chunks/sec)
- **Regression test harness** — describe how to use `MetricsCollector`'s `BenchmarkRunner` to store baseline metrics and detect regressions in CI (NixOS `nix flake check` hook)

---

## SECTION 8 — Edge Cases and Failure Modes

Enumerate at least 15 specific edge cases across all three subsystems, each with: description, likely cause, detection method, and mitigation strategy. Examples to include and expand upon:

- Ollama embedding server unavailable at index query time
- FAISS index corrupted on disk (partial write during crash)
- Chain YAML references a tool not present in ToolRegistry
- Parallel group timeout with partial completions — how is partial output handled?
- Cloud API key present but rate limit hit mid-chain
- Self-correction loop producing the same incorrect output on all attempts
- AST parsing failure on syntactically invalid Python file during ingestion
- Vault unreachable when SecureAPIHandler initializes
- MetricsDB (SQLite) locked by concurrent writers
- Jinja2 conditional expression in YAML chain raises exception
- Embedding dimension mismatch between old and new model (index rebuild required)
- PromptRefiner injects too much context, exceeding model context window
- AutoReindexTimer fires during an active chain using the index
- Cost budget exceeded mid-session — how does HybridRouter degrade gracefully?
- Lua plugin keybinding conflicts with existing Neovim config

---

## SECTION 9 — Learning Elevation

Conclude with a 200-word section explaining, from a pedagogical perspective, how these improvements collectively elevate Jarvis from a coding assistant into a genuine AI reasoning environment for learning programming and AI systems design. Address: how adaptive ERS chains teach users to think in terms of composable, fault-tolerant pipelines; how semantic indexing over one's own codebase creates a personalized knowledge graph that accelerates comprehension; how honest metrics make AI performance legible and non-magical; and how the hybrid routing model demonstrates real-world cost/quality tradeoff reasoning. This section is for the human reading the Antigravity output — write it in second person ("you"), addressing the Jarvis user directly.

---

## OUTPUT REQUIREMENTS

- All Python code must be Python 3.11+, fully typed, `ruff`-compliant, and `mypy`-strict compatible
- All Nix expressions must be compatible with Nix flakes (no legacy `nix-env` patterns)
- All YAML examples must be valid and parseable by the Pydantic schemas you define
- Mermaid diagrams must use only standard Mermaid syntax (no plugins)
- Do not omit any section. Do not produce stubs or placeholders. Every function must have a real body.
- If a complete implementation would exceed your context, prioritize depth over breadth: produce fewer but complete modules rather than many skeleton files
- Maintain the offline-first constraint throughout: every feature must degrade gracefully when network is unavailable, and no feature should require cloud access to function at a basic level

Begin output now.
