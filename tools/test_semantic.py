import sys
import os
import sqlite3
from pathlib import Path

# Ensure Jarvis root is in PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.semantic_memory import SemanticMemory

def run_tests():
    # Setup a fresh memory instance
    sm = SemanticMemory()
    import lib.semantic_memory
    print(f"DEBUG: Using SemanticMemory from {lib.semantic_memory.__file__}")
    db_path = sm.db_path
    
    print("Testing semantic ingestion (Phase 5)...")
    content = "Hello, I am Jarvis. I am a specialized AI coding assistant built in NixOS and Python."
    meta = {"source": "test", "type": "intro"}
    
    # 1. Ingest
    sm.ingest(content, metadata=meta, layer=1, category="test_knowledge")
    
    # Check if written to db
    conn = sm._get_connection()
    count = conn.execute("SELECT COUNT(*) FROM chunk_metadata WHERE category='test_knowledge'").fetchone()[0]
    assert count > 0, "Ingestion failed to write metadata"
    
    count_vec = conn.execute("SELECT COUNT(*) FROM vec_chunks").fetchone()[0]
    assert count_vec > 0, "Ingestion failed to write vec_chunks"
    
    # 2. Query
    print("Testing semantic query via sqlite-vec...")
    results = sm.query("Who is Jarvis?", k=1, category="test_knowledge")
    assert len(results) > 0, "Query returned zero results"
    
    res = results[0]
    assert "AI coding assistant" in res.content, f"Content doesn't match: {res.content}"
    assert res.score > 0, f"Expected positive similarity score, got {res.score}"
    assert res.metadata['category'] == "test_knowledge"
    
    print("Success: test_semantic passed.")
    
    # 3. Entities
    print("Testing entity extraction (Phase 6)...")
    entity_count = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
    if entity_count == 0:
        # Check if there was an error emitted or if it just returned empty
        print("DEBUG: Entity count is 0. Checking if extraction logic was reached.")
    assert entity_count > 0, "Ingestion failed to extract entities"
    entities = conn.execute("SELECT subject, relation, object FROM entities").fetchall()
    print("Extracted Triples:")
    for e in entities:
        print(f"  - {e[0]} --[{e[1]}]--> {e[2]}")

if __name__ == "__main__":
    run_tests()
