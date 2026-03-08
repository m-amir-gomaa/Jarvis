import sqlite3
import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import os
# /home/qwerty/NixOSenv/Jarvis/lib/knowledge_manager.py

BASE_DIR = Path(os.environ.get("JARVIS_ROOT", Path(__file__).resolve().parent.parent))
KNOWLEDGE_DB = BASE_DIR / "data" / "knowledge.db"

class KnowledgeManager:
    """
    KnowledgeManager wraps the new Indexing/RAG pipeline while preserving
    the legacy SQLite-based metadata API.
    """
    def __init__(self, db_path: Path = KNOWLEDGE_DB):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        
        # New Agentic Intel components
        from lib.indexing.embedding_engine import EmbeddingEngine
        from lib.indexing.faiss_index import FAISSIndexManager
        from lib.indexing.semantic_search import SemanticSearch
        
        self.embeddings = EmbeddingEngine()
        self.faiss = FAISSIndexManager(
            index_path=str(BASE_DIR / "index" / "faiss.bin"),
            meta_db_path=str(db_path) # Shares the same DB for metadata
        )
        self.semantic_search_engine = SemanticSearch(self.embeddings, self.faiss)

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            # Create chunks table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    layer INTEGER NOT NULL,
                    category TEXT,
                    source_url TEXT,
                    source_title TEXT,
                    content TEXT NOT NULL,
                    embedding BLOB,
                    metadata TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create inbox table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS inbox (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT,
                    title TEXT NOT NULL,
                    url TEXT,
                    recommendation_reason TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # codebase_associations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS codebase_associations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT NOT NULL,
                    category TEXT NOT NULL,
                    UNIQUE(path, category)
                )
            """)
            
            conn.execute("CREATE INDEX IF NOT EXISTS idx_layer ON chunks(layer)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON chunks(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON chunks(source_url)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_assoc_path ON codebase_associations(path)")

    def add_entry(self, layer: int, content: str, source_url: Optional[str] = None, 
                  source_title: Optional[str] = None, category: Optional[str] = None, 
                  metadata: Optional[Dict] = None):
        """Standard entry addition (legacy wrapper)."""
        # In the new system, we rely on the Ingestor, but for manual adds:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO chunks (layer, category, source_url, source_title, content, metadata) VALUES (?, ?, ?, ?, ?, ?)",
                (layer, category, source_url, source_title, content, json.dumps(metadata or {}))
            )
        # Note: Incremental FAISS update should happen via AutoReindex or manual trigger

    def update_entry(self, source_url: str, content: str, category: Optional[str] = None, metadata: Optional[Dict] = None):
        """Legacy update wrapper."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM chunks WHERE source_url = ?", (source_url,))
        self.add_entry(2, content, source_url, category=category, metadata=metadata)

    async def search(self, query_text: str, layer: Optional[int] = None, category: Optional[str] = None, categories: Optional[List[str]] = None) -> List[Dict]:
        """
        Unified search using the new hybrid SemanticSearch engine.
        """
        filters = {}
        if category:
            filters["category"] = category
            
        # Note: Hybrid search currently doesn't support multiple categories natively in the loop,
        # but we can filter the result set later.
        
        result_set = await self.semantic_search_engine.search(query_text, top_k=10, filters=filters if filters else None)
        
        legacy_results = []
        for r in result_set.results:
            # Filter by layer if requested
            chunk_layer = r.extra_meta.get('layer')
            if layer and chunk_layer != layer:
                continue
            # Filter by multiple categories if requested
            if categories and r.chunk_type not in categories and r.extra_meta.get('category') not in categories:
                continue

            legacy_results.append({
                'content': r.content,
                'source_url': r.source_path,
                'source_title': r.extra_meta.get('title', ''),
                'category': r.extra_meta.get('category', r.chunk_type),
                'layer': chunk_layer
            })
            
        return legacy_results

    def associate_path(self, path: str, category: str):
        abs_path = str(Path(path).resolve())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO codebase_associations (path, category) VALUES (?, ?)",
                (abs_path, category)
            )

    def unassociate_path(self, path: str, category: Optional[str] = None):
        abs_path = str(Path(path).resolve())
        with sqlite3.connect(self.db_path) as conn:
            if category:
                conn.execute(
                    "DELETE FROM codebase_associations WHERE path = ? AND category = ?",
                    (abs_path, category)
                )
            else:
                conn.execute(
                    "DELETE FROM codebase_associations WHERE path = ?",
                    (abs_path,)
                )

    def get_associations(self, path: str) -> List[str]:
        current_path = Path(path).resolve()
        associations = set()
        
        with sqlite3.connect(self.db_path) as conn:
            while True:
                rows = conn.execute(
                    "SELECT category FROM codebase_associations WHERE path = ?",
                    (str(current_path),)
                ).fetchall()
                for row in rows:
                    associations.add(row[0])
                
                if current_path == current_path.parent:
                    break
                current_path = current_path.parent
                
        return list(associations)
