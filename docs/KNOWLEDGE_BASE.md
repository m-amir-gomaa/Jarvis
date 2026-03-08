# Jarvis Knowledge Base & Indexing (Deep Dive)

Jarvis V3 implements a sophisticated Retrieval-Augmented Generation (RAG) system designed for low-latency, high-precision context injection. If you're new to these concepts, read the **[AI Terminology Guide](AI_TERMINOLOGY.md)** first. This document details the technical implementation of the indexing pipeline and the 3-Layer knowledge architecture.

## 1. The 3-Layer Architecture

Jarvis categorizes all ingested knowledge into three distinct layers to manage retrieval priority and noise:

1.  **Layer 1 (Language & Identity)**: Core system prompts, communication styles, and basic reasoning patterns. This is Jarvis's "ego."
2.  **Layer 2 (Domain & Codebase)**: Project-specific documentation, file indexes, and technical specifications. This is Jarvis's "expertise."
3.  **Layer 3 (Theory & Research)**: Broad academic papers, books, and external tutorials. This is Jarvis's "library."

## 2. Technical Stack

*   **Database**: SQLite 3.44+ with the `sqlite-vec` extension for native vector search.
*   **Vector Engine**: `vec0` virtual tables for high-performance K-Nearest Neighbors (KNN) search.
*   **Embeddings**: 768-dimensional vectors generated via Ollama (typically using `nomic-embed-text`).
*   **Knowledge Graph**: An `entities` table storing triples (Subject-Relation-Object) extracted via LLM analysis during ingestion.

## 3. The Indexing Pipeline

When a document is ingested (via `jarvis learn` or `jarvis index`), it undergoes the following stages:

### A. Pre-Processing & Chunking
Jarvis uses a hybrid chunking strategy implemented in `lib/semantic_memory.py`:
- **Recursive Character Splitting**: Splitting by double newlines, single newlines, or sentences to maintain semantic coherence.
- **Strategy-Based Splitting**: (`tools/chunker.py`) Supports `heading` (markdown headers), `tokens` (fixed-size with overlap), and `page` (horizontal rules) modes.

### B. Vector Embedding
Each chunk is sent to the local Ollama instance. The resulting 768-float vector is packed into a binary BLOB using standard Little-Endian padding (`struct.pack("<768f")`) and stored in the `vec_chunks` table.

### C. Entity Extraction (Semantic Graph)
Concurrent with embedding, a subset of chunks is processed by a fast LLM (e.g., `qwen3:1.7b`) to extract factual relationships. 
- **Example**: `[["NixOS", "utilizes", "systemd"], ["Jarvis", "runs_on", "NixOS"]]`
- These triples are stored in the `entities` table, allowing for future graph-based traversal alongside vector search.

## 4. Retrieval & RAG Logic

When you run `jarvis query`, the following happens:

1.  **Dense Retrieval**: The query is embedded, and a KNN search is performed against `vec_chunks` using cosine distance. 
2.  **Hybrid Filtering**: Results are filtered by `category` or `layer` if specified. If filtering is active, the initial search space (`k`) is dynamically expanded to ensure high recall.
3.  **Context Synthesis**: Top results (typically Top-5) are combined with **Episodic Memory** (the current chat session context).
4.  **Reality Injection**: The context is injected into the LLM via a system prompt that instructs Jarvis to "internalize" this data as its own personal identity and knowledge, rather than treating it as external snippets.

## 5. Performance Optimizations

- **FTS5 Fallback**: While primary search is vector-based, the system includes logic for keyword-based fallback if high-confidence vectors are not found.
- **Local-First**: Complete privacy is maintained by performing all embedding and search operations on the local machine (NixOS system) without external API calls.

---
*For implementation details, see [lib/knowledge_manager.py](../lib/knowledge_manager.py) and [lib/semantic_memory.py](../lib/semantic_memory.py).*
