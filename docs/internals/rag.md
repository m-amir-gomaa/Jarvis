# Internal: Indexing & RAG Pipeline

Jarvis v3.5 implements a local-first **Retrieval-Augmented Generation (RAG)** system using FAISS and Ollama.

## 🏗️ Architecture

### Vector Store (`lib/indexing/faiss_index.py`)
*   **FAISS (Facebook AI Similarity Search)**: Stores high-dimensional vectors for fast nearest-neighbor search.
*   **SQLite Metadata**: A companion `metadata.db` maps vector IDs to file paths, line numbers, and raw text chunks.
*   **Indexing Logic**: Uses `IndexIDMap` with `IndexFlatIP` (Inner Product) to support persistent IDs and cosine similarity.

### Embedding Engine (`lib/indexing/embedding_engine.py`)
*   **Primary**: `nomic-embed-text` via Ollama (768 dimensions).
*   **Fallback**: `all-MiniLM-L6-v2` via `sentence-transformers` for offline/CPU-only scenarios.
*   **Caching**: Normalized embeddings are cached in `~/.jarvis/index/cache` (deterministically hashed) to avoid redundant LLM calls.

### Ingestion Pipeline (`lib/indexing/ingestor.py`)
The `IngestionWorker` performs language-aware chunking:
*   **Python**: AST-based parsing extracts classes and functions as atomic chunks.
*   **Markdown**: Sliding window paragraph chunking with context overlap.
*   **Rust/Lua**: Regex-based function boundary detection.

### Background Service (`services/jarvis_indexer.py`)
*   **Event-Driven**: Uses `watchdog` to monitor the workspace for file changes.
*   **Debounced**: Indexing triggers only after a 2-second "quiet period" to handle rapid saves.
*   **Scheduled**: Full daily re-indexing via `apscheduler`.

## 🔍 Search Process

1.  **Query Embedding**: User input is converted to a vector.
2.  **Similarity Search**: FAISS retrieves the top-K (default 5) most relevant chunk IDs.
3.  **Metadata Join**: SQLite fetches the raw text and source location (file/line).
4.  **Context Injection**: Chunks are injected into the LLM prompt as "Supplied Context".

## 🛠️ Maintenance

To manually rebuild the index:
```bash
jarvis index --rebuild
```
Or use the Neovim command:
```vim
:JarvisIndex
```
