# Jarvis Knowledge Base & Indexing (Deep Dive)

Jarvis V3 implements a sophisticated Retrieval-Augmented Generation (RAG) system designed for low-latency, high-precision context injection. If you're new to these concepts, read the **[AI Terminology Guide](AI_TERMINOLOGY.md)** first. This document details the technical implementation of the indexing pipeline and the 3-Layer knowledge architecture.

## 1. The 3-Layer Architecture

Jarvis categorizes all ingested knowledge into three distinct layers to manage retrieval priority and noise:

1.  **Layer 1 (Language & Identity)**: Core system prompts, communication styles, and basic reasoning patterns. This is Jarvis's "ego."
2.  **Layer 2 (Domain & Codebase)**: Project-specific documentation, file indexes, and technical specifications. This is Jarvis's "expertise."
3.  **Layer 3 (Theory & Research)**: Broad academic papers, books, and external tutorials. This is Jarvis's "library."

## 2. Technical Stack

*   **Vector Engine**: FAISS (Facebook AI Similarity Search) for high-performance Approximate Nearest Neighbor (ANN) search.
*   **Metadata Storage**: `aiosqlite` for asynchronous persistent metadata mapping.
*   **Index Types**: 
    - `flat_ip`: Inner Product (IP) index for exact search on smaller datasets.
    - `ivf_pq`: Inverted File Index with Product Quantization for memory-efficient projection on large datasets.
*   **Embeddings**: 768-dimensional vectors generated via local projection engines (typically using `nomic-embed-text`).

## 3. The Indexing Pipeline

When a document is ingested (via `jarvis learn` or `jarvis index`), it undergoes the following stages:

### A. Intelligence-Based Chunking
Jarvis uses a language-aware chunking strategy implemented in `lib/indexing/ingestor.py` to maintain "Multi-dimensional Vector Projection" (not "Semantic Understanding"):
- **Python**: AST-based extraction of functions, classes, and async definitions.
- **Rust/Lua**: RegEx-based boundary detection for function-level scoping.
- **Markdown**: Sliding window paragraph grouping to maintain narrative context.

### B. Index Sharding & Training
For `ivf_pq` indices, the system accumulates a representative training set (2x `nlist`) before executing the quantization transformation. This ensures stable clusters within the vector space.

### C. Episodic State Serialization
Metadata (line numbers, source paths, node names) is serialized into the companion SQLite database, linking the content-addressable vector IDs to their physical source locations.

## 4. Hybrid Retrieval & RRF Logic

When a query is processed, the system executes a "Hybrid Retrieval" flow to ensure high recall and precision:

1.  **Dense Vector Search**: The query is projected into the vector space, and the Top-K candidates are retrieved from the FAISS index.
2.  **Metadata Filtering**: Sub-millisecond filtering is applied based on `category`, `source_path`, or `layer` using the `aiosqlite` index.
3.  **BM25 Re-Ranking**: A dependency-free BM25 implementation re-scores the candidates based on keyword frequency to capture exact terminology that vector projections might blur.
4.  **Score Normalization**: Multi-modal scores are normalized and combined using a weighted sum (Alpha-blending) to produce the final `hybrid_score`.
5.  **Context Construction**: The highest-scoring fragments are retrieved and formatted for injection into the prompt context.

## 5. Performance Optimizations

- **Quantized Storage**: IVF-PQ reduces memory footprint by ~10-20x compared to flat float32 vectors.
- **Lazy Load**: The vector store and embedding engines are lazily initialized only when a search operation is triggered.
- **Content-Addressable**: Duplicate content is naturally deduplicated via chunk ID hashing, preventing redundant index entries.

---
*For implementation details, see [lib/indexing/faiss_index.py](../lib/indexing/faiss_index.py), [lib/indexing/semantic_search.py](../lib/indexing/semantic_search.py), and [lib/indexing/ingestor.py](../lib/indexing/ingestor.py).*
