import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path
from lib.indexing.auto_reindex import AutoReindexTimer

@pytest.fixture
def mock_deps():
    faiss_mgr = AsyncMock()
    ingestor = MagicMock()
    emb_engine = AsyncMock()
    return faiss_mgr, ingestor, emb_engine

@pytest.fixture
def reindexer(mock_deps, tmp_path):
    faiss_mgr, ingestor, emb_engine = mock_deps
    timer = AutoReindexTimer(str(tmp_path), faiss_mgr, ingestor, emb_engine, debounce_seconds=0.1)
    return timer

def test_is_valid_file(reindexer):
    assert reindexer._is_valid_file("test.py") is True
    assert reindexer._is_valid_file("test.md") is True
    assert reindexer._is_valid_file("test.txt") is False
    assert reindexer._is_valid_file(".hidden.py") is False
    assert reindexer._is_valid_file(".venv/lib/test.py") is False

@pytest.mark.asyncio
async def test_debounce_and_update(reindexer, mock_deps, tmp_path):
    faiss_mgr, ingestor, emb_engine = mock_deps
    
    # Mock ingestor processing
    mock_chunk = MagicMock()
    mock_chunk.chunk_id = "1"
    mock_chunk.chunk_type = "PY"
    mock_chunk.content = "print"
    mock_chunk.start_line = 1
    mock_chunk.end_line = 2
    mock_chunk.extra_meta = {}
    ingestor.process_file.return_value = [mock_chunk]
    
    # Mock embedding
    import numpy as np
    emb_engine.embed_batch.return_value = np.array([[0.1, 0.2]])

    test_file = tmp_path / "test.py"
    
    # Fire events rapidly
    reindexer._schedule_update(str(test_file), is_delete=False)
    reindexer._schedule_update(str(test_file), is_delete=False)
    
    # Wait for debounce
    await asyncio.sleep(0.2)
    
    # The faiss delete_by_source should have been called once for the file update
    faiss_mgr.delete_by_source.assert_called_once_with(str(test_file))
    
    # Embedding was requested
    emb_engine.embed_batch.assert_called_once_with(["print"])
    
    # Faiss add was called once
    faiss_mgr.add.assert_called_once()

@pytest.mark.asyncio
async def test_scheduled_delete(reindexer, mock_deps):
    faiss_mgr, _, _ = mock_deps
    
    reindexer._schedule_update("deleted.py", is_delete=True)
    await asyncio.sleep(0.2)
    
    faiss_mgr.delete_by_source.assert_called_once_with("deleted.py")

@pytest.mark.asyncio
async def test_start_stop(reindexer, mock_deps):
    faiss_mgr, _, _ = mock_deps
    
    try:
        reindexer.start()
        # Verify apscheduler has the task
        jobs = reindexer.scheduler.get_jobs()
        assert len(jobs) == 1
    finally:
        reindexer.stop()
