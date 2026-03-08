# Prompt for Agent 2: Indexing & RAG Pipeline Implementation

You are an expert systems architect and senior engineer embedded in the Jarvis project — a NixOS-based AI orchestrator. 

Your sole responsibility is to implement the **Indexing and RAG Upgrade** on the isolated branch `Jarvis_agentic_intel_indexing`.

## Step 1: Bootstrap & Persistence
You are operating in an environment where your quota or context window may exhaust.
1. `git checkout Jarvis_agentic_intel_indexing` (if not already on it).
2. Immediately create or update a file named `BOOTSTRAP_INDEXING.md` in the project root.
3. This file MUST contain:
   - Your current assigned task (e.g., "Implementing faiss_index.py").
   - A checklist of files completed and passing tests.
   - Any unresolved bugs or type errors.
   - The immediate next step to perform.
   - **A dedicated section tracking the completion of the comprehensive test suite.**
4. Update `BOOTSTRAP_INDEXING.md` continuously. If your session is restarted, you must read this file first to resume seamlessly.

## Step 2: Constraints
- You may ONLY modify files in `lib/indexing/` and tests relating to Indexing.
- Do NOT touch `lib/ers/`, `lib/models/`, or `services/jarvis_lsp.py`.
- All Python code must be Python 3.11+, `ruff`-compliant, and `mypy`-strict compatible.
- Rely on `faiss-cpu`, `sentence-transformers`, `watchdog`, `apscheduler`, and `aiosqlite`.
- Practice TDD. Write unit tests as you build. Commit working increments.

## Step 3: Architecture to Implement
Implement the following 5 modules in `lib/indexing/`:

### 1. `embedding_engine.py`
- Local-first embeddings. Primary: Ollama (`nomic-embed-text`). Secondary fallback: `sentence-transformers`.
- Cache vectors to disk. Support batching arrays (`numpy`). Includes cosine similarity utility.

### 2. `faiss_index.py`
- Persistent `faiss-cpu` vector store (`IndexFlatIP`/`IndexIVFFlat`).
- Persist to `~/.jarvis/index/faiss.bin` and a companion SQLite DB for metadata mapping.
- Async locking for thread safety. Expose `add`, `search`, `delete_by_source`, `rebuild`.

### 3. `ingestor.py`
- Implement `IngestionWorker` for multi-modal files.
- **Python**: AST parsing for functions/classes/docstrings.
- **Markdown**: Sliding window paragraph chunks.
- **Rust/Lua**: Regex boundaries for functions/structs.
- Represent outputs as a normalized `Chunk` dataclass.

### 4. `semantic_search.py`
- Combine vector similarity (FAISS) with BM25 keyword scoring over the Metadata DB.
- Filter by `chunk_type`, `source_path`, etc.
- Return a ranked `SearchResultSet` with latency stats.

### 5. `auto_reindex.py`
- Implement `AutoReindexTimer`. Uses `watchdog` to monitor working directories.
- Debounce rapid changes (e.g., 2 seconds).
- Delete old file chunks, re-ingest, incrementally update FAISS index.
- Setup cron schedules via `apscheduler`.

## Step 4: Final Hand-off & Test Suite
Before you are finished, you MUST produce a comprehensive test suite in `tests/indexing/`. 
- Write unit tests for every new class using `pytest` and `pytest-asyncio`. 
- Include at least 3 test cases per module: happy path, failure/edge case, and async concurrency behavior. 
- Use `unittest.mock` for any external dependencies (like Ollama or filesystem watchers).

Once all implementations are complete and your comprehensive test suite passes locally, commit all changes, push your branch, update `BOOTSTRAP_INDEXING.md` marking Phase 1 & Testing Complete, and notify the user.
