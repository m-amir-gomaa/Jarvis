import pytest
import os
import faiss
import asyncio
from unittest.mock import patch
from pathlib import Path
from lib.indexing.faiss_index import FaissIndexManager

@pytest.fixture
def faiss_manager(tmp_path):
    # Using small dimension for testing 
    mgr = FaissIndexManager(index_dir=str(tmp_path), dimension=4)
    return mgr

@pytest.mark.asyncio
async def test_faiss_initialize(faiss_manager):
    await faiss_manager.initialize()
    assert faiss_manager.db_path.exists()
    assert faiss_manager.index is not None
    assert faiss_manager.index.ntotal == 0

@pytest.mark.asyncio
async def test_faiss_add_and_search(faiss_manager):
    await faiss_manager.initialize()
    
    vec1 = [1.0, 0.0, 0.0, 0.0]
    vec2 = [0.0, 1.0, 0.0, 0.0]
    vec3 = [0.707, 0.707, 0.0, 0.0] # 45 degrees
    
    await faiss_manager.add("chunk1", "test.py", "AST", "foo()", vec1)
    await faiss_manager.add("chunk2", "test.py", "AST", "bar()", vec2)
    
    assert faiss_manager.index.ntotal == 2
    
    # Search for something close to vec1
    # We query with slightly offset vector
    results = await faiss_manager.search(vec1, top_k=2)
    assert len(results) == 2
    assert results[0]["chunk_id"] == "chunk1"
    assert results[0]["score"] > 0.9  # Should be ~1.0 since it's an exact match
    
    # Search close to vec2
    results_2 = await faiss_manager.search([0.1, 0.9, 0.0, 0.0], top_k=1)
    assert len(results_2) == 1
    assert results_2[0]["chunk_id"] == "chunk2"

@pytest.mark.asyncio
async def test_faiss_update_duplicate(faiss_manager):
    await faiss_manager.initialize()
    
    vec1 = [1.0, 0.0, 0.0, 0.0]
    vec2 = [0.0, 1.0, 0.0, 0.0]

    await faiss_manager.add("chunkA", "file.md", "MD", "content1", vec1)
    
    # Adding same chunk_id should update/remove the old one preventing duplicates
    await faiss_manager.add("chunkA", "file.md", "MD", "content2", vec2)
    
    # Verify index total is 1
    assert faiss_manager.index.ntotal == 1
    
    results = await faiss_manager.search(vec2, top_k=1)
    assert results[0]["content"] == "content2"
    
@pytest.mark.asyncio
async def test_faiss_delete_by_source(faiss_manager):
    await faiss_manager.initialize()
    await faiss_manager.add("c1", "a.py", "AST", "funcA", [1.,0.,0.,0.])
    await faiss_manager.add("c2", "a.py", "AST", "funcB", [0.,1.,0.,0.])
    await faiss_manager.add("c3", "b.py", "AST", "funcC", [0.,0.,1.,0.])
    
    assert faiss_manager.index.ntotal == 3
    
    await faiss_manager.delete_by_source("a.py")
    
    assert faiss_manager.index.ntotal == 1
    
    results = await faiss_manager.search([0.,0.,1.,0.], top_k=1)
    assert results[0]["chunk_id"] == "c3"
    
@pytest.mark.asyncio
async def test_faiss_rebuild(faiss_manager):
    await faiss_manager.initialize()
    await faiss_manager.add("c1", "f.py", "AST", "hello", [1.,0.,0.,0.])
    
    await faiss_manager.rebuild()
    
    assert faiss_manager.index.ntotal == 0
    # Directory contents might still have empty faiss.bin due to initialization
    assert faiss_manager.db_path.exists()
