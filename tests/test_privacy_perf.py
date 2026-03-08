# tests/test_privacy_perf.py
import pytest
import os
import json
import numpy as np
import tempfile
from pathlib import Path

from lib.indexing.faiss_index import FaissIndexManager
from lib.model_router import route, route_fim_draft, Privacy, RouteDecision
from lib.llm import _is_confidential, ask, ConfidentialModeViolation

@pytest.fixture
def temp_index_dir():
    with tempfile.TemporaryDirectory() as td:
        yield td

@pytest.mark.asyncio
async def test_ivf_pq_index_training(temp_index_dir):
    """Test that IVF-PQ index can be created, trained, and searched."""
    # We need dim=32 for a quick test so PQ_M=16 subquantizers works (32 % 16 == 0)
    dim = 32
    manager = FaissIndexManager(index_dir=temp_index_dir, dimension=dim, index_type="ivf_pq")
    await manager.initialize()

    assert manager.index_type == "ivf_pq"
    assert not manager._ivf_trained
    assert manager.memory_estimate_mb == 0.0

    # Generate random test vectors (need 2 * 128 = 256 for _IVF_NLIST=128)
    n_vectors = 300
    vectors = np.random.randn(n_vectors, dim).astype(np.float32).tolist()

    # Train manually
    await manager.train_from_vectors(vectors)
    assert manager._ivf_trained
    
    # Add vectors
    for i, vec in enumerate(vectors):
        await manager.add(
            chunk_id=f"chunk_{i}",
            source_path="test.py",
            chunk_type="code",
            content=f"def test_{i}(): pass",
            embedding=vec
        )

    assert manager.index.ntotal == n_vectors
    
    # Search should work
    res = await manager.search(vectors[0], top_k=2)
    assert len(res) > 0
    assert res[0]["chunk_id"] == "chunk_0"  # Should be the closest since it's exact

def test_fim_draft_routing():
    """Test latency-optimised routing for FIM draft mode."""
    decision = route_fim_draft(privacy=Privacy.PUBLIC)
    
    assert decision.use_local is True
    assert decision.provider == "ollama"
    # Even if public, FIM drafts must be local
    assert "FIM draft mode" in decision.reasoning
    assert decision.model_alias == "qwen2.5-coder:0.5b-instruct"

def test_confidential_mode_detection(temp_index_dir):
    """Test that _is_confidential correctly reads workspace and global config."""
    ws = Path(temp_index_dir)
    jarvis_dir = ws / ".jarvis"
    jarvis_dir.mkdir()
    cfg_file = jarvis_dir / "config.toml"
    
    assert not _is_confidential(workspace_dir=str(ws))

    cfg_file.write_text("confidential = true\n")
    assert _is_confidential(workspace_dir=str(ws)) is True
    
    cfg_file.write_text("confidential = false\n")
    assert _is_confidential(workspace_dir=str(ws)) is False

def test_confidential_mode_violation(monkeypatch, temp_index_dir):
    """Test that ask() raises ConfidentialModeViolation when routing externally."""
    ws = Path(temp_index_dir)
    (ws / ".jarvis").mkdir()
    (ws / ".jarvis" / "config.toml").write_text("confidential = true\n")

    # Mock route to return a cloud backend (simulating a PUBLIC task requested)
    def mock_route(*args, **kwargs):
        return RouteDecision(
            use_local=False, 
            model_alias="claude-3-haiku", 
            provider="openrouter", 
            reasoning="test"
        )
    
    monkeypatch.setattr("lib.model_router.route", mock_route)
    
    # Mock router instance so ask() attempts to use v2 routing
    class MockRouter:
        def call(self, *args, **kwargs):
            return "response", {}
            
    monkeypatch.setattr("lib.llm._get_router", lambda: MockRouter())

    with pytest.raises(ConfidentialModeViolation) as exc:
        ask("hello", privacy=Privacy.PUBLIC, ctx="mock_ctx", workspace_dir=str(ws))
        
    assert "confidential mode is active" in str(exc.value)
    assert "claude-3-haiku" in str(exc.value)
