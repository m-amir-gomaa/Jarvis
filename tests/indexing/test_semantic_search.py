import pytest
import math
from unittest.mock import AsyncMock, MagicMock
from lib.indexing.semantic_search import SemanticSearch, BM25Scorer

def test_bm25_scorer():
    corpus = [
        "The quick brown fox jumps over the lazy dog",
        "Python is a great programming language",
        "The dog is lazy but the fox is quick"
    ]
    scorer = BM25Scorer(corpus)
    
    # "fox" should score higher in doc 0 and 2
    s0 = scorer.score("fox dog", 0)
    s1 = scorer.score("fox dog", 1)
    s2 = scorer.score("fox dog", 2)
    
    assert s0 > s1
    assert s2 > s1
    assert s1 == 0.0 # No matches in doc 1

@pytest.fixture
def mock_embedding():
    engine = AsyncMock()
    # Mocking standard vector
    engine.embed_text.return_value = [0.1, 0.2, 0.3]
    return engine

@pytest.fixture
def mock_faiss():
    mgr = AsyncMock()
    # Mocking returning 3 db entries
    mgr.search.return_value = [
        {"chunk_id": "c1", "source_path": "a.py", "chunk_type": "PY", "content": "func hello()", "start_line": 1, "end_line": 2, "extra_meta": {}, "score": 0.9},
        {"chunk_id": "c2", "source_path": "b.py", "chunk_type": "PY", "content": "class World", "start_line": 1, "end_line": 2, "extra_meta": {}, "score": 0.8},
        {"chunk_id": "c3", "source_path": "c.md", "chunk_type": "MD", "content": "hello world from markdown", "start_line": 1, "end_line": 2, "extra_meta": {}, "score": 0.7}
    ]
    return mgr

@pytest.mark.asyncio
async def test_semantic_search_hybrid(mock_embedding, mock_faiss):
    searcher = SemanticSearch(mock_embedding, mock_faiss)
    
    # The query mentions "markdown", which is explicitly in c3's content.
    # While c1 has highest vector score (0.9), BM25 should boost c3.
    res = await searcher.search("markdown hello", top_k=3, alpha=0.5)
    
    assert res.query == "markdown hello"
    assert res.latency_ms >= 0
    assert len(res.results) == 3
    
    # Check that scores exist
    for r in res.results:
        assert r.hybrid_score is not None
        assert r.bm25_score >= 0.0

@pytest.mark.asyncio
async def test_semantic_search_filters(mock_embedding, mock_faiss):
    searcher = SemanticSearch(mock_embedding, mock_faiss)
    
    # Filter by chunk_type == "MD"
    res = await searcher.search("hello", top_k=3, alpha=1.0, filters={"chunk_type": "MD"})
    
    assert len(res.results) == 1
    assert res.results[0].chunk_id == "c3"

@pytest.mark.asyncio
async def test_semantic_search_no_embeddings(mock_embedding, mock_faiss):
    mock_embedding.embed_text.return_value = None
    searcher = SemanticSearch(mock_embedding, mock_faiss)
    res = await searcher.search("fail me")
    assert len(res.results) == 0
