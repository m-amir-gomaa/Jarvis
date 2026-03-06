import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# /THE_VAULT/jarvis/lib/knowledge_manager.py

KNOWLEDGE_DB = Path("/THE_VAULT/jarvis/data/knowledge.db")

class KnowledgeManager:
    def __init__(self, db_path: Path = KNOWLEDGE_DB):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            # Create chunks table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    layer INTEGER NOT NULL, -- 1: Language, 2: Domain, 3: Theory
                    category TEXT, -- Added category for RAG grouping
                    source_url TEXT,
                    source_title TEXT,
                    content TEXT NOT NULL,
                    embedding BLOB, -- For future local vector search
                    metadata TEXT, -- JSON string (tags, language, section)
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create inbox table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS inbox (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT, -- Added type for filtering
                    title TEXT NOT NULL,
                    url TEXT,
                    recommendation_reason TEXT,
                    status TEXT DEFAULT 'pending', -- pending, downloading, completed
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Indices
            conn.execute("CREATE INDEX IF NOT EXISTS idx_layer ON chunks(layer)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON chunks(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON chunks(source_url)")
            
            # Migration: Migration logic for existing installations
            self._migrate_schema(conn)

    def _migrate_schema(self, conn: sqlite3.Connection):
        # 1. Check if 'knowledge' table exists and merge it into 'chunks'
        res = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge'").fetchone()
        if res:
            print("[KnowledgeManager] Merging legacy 'knowledge' table into 'chunks'...")
            # Copy data, avoiding ID collisions if possible or just fresh IDs
            conn.execute("""
                INSERT INTO chunks (layer, category, source_url, source_title, content, embedding, metadata, last_updated)
                SELECT layer, 'legacy', source_url, source_title, content, embedding, metadata, last_updated 
                FROM knowledge k
                WHERE NOT EXISTS (SELECT 1 FROM chunks c WHERE c.content = k.content)
            """)
            conn.execute("DROP TABLE knowledge")
            print("[KnowledgeManager] Migration complete.")

        # 2. Check if 'inbox' has 'type' column
        cursor = conn.execute("PRAGMA table_info(inbox)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'type' not in columns:
            print("[KnowledgeManager] Adding 'type' column to 'inbox'...")
            conn.execute("ALTER TABLE inbox ADD COLUMN type TEXT")

        # 3. Check if 'chunks' has 'category' column (it should if created by IF NOT EXISTS above)
        cursor = conn.execute("PRAGMA table_info(chunks)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'category' not in columns:
             print("[KnowledgeManager] Adding 'category' column to 'chunks'...")
             conn.execute("ALTER TABLE chunks ADD COLUMN category TEXT")

    def add_entry(self, layer: int, content: str, source_url: Optional[str] = None, 
                  source_title: Optional[str] = None, category: Optional[str] = None, 
                  metadata: Optional[Dict] = None):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO chunks (layer, category, content, source_url, source_title, metadata) VALUES (?, ?, ?, ?, ?, ?)",
                (layer, category, content, source_url, source_title, json.dumps(metadata or {}))
            )

    def update_entry(self, source_url: str, content: str, category: Optional[str] = None, metadata: Optional[Dict] = None):
        with sqlite3.connect(self.db_path) as conn:
            if category:
                conn.execute(
                    "UPDATE chunks SET content = ?, category = ?, metadata = ?, last_updated = CURRENT_TIMESTAMP WHERE source_url = ?",
                    (content, category, json.dumps(metadata or {}), source_url)
                )
            else:
                conn.execute(
                    "UPDATE chunks SET content = ?, metadata = ?, last_updated = CURRENT_TIMESTAMP WHERE source_url = ?",
                    (content, json.dumps(metadata or {}), source_url)
                )

    def set_identity(self, identity_text: str):
        with sqlite3.connect(self.db_path) as conn:
            # Delete old identity chunks to avoid duplicates
            conn.execute("DELETE FROM chunks WHERE category = 'identity'")
            conn.execute(
                "INSERT INTO chunks (layer, category, source_title, source_url, content) VALUES (?, ?, ?, ?, ?)",
                (1, "identity", "System Identity", "internal://identity", identity_text)
            )

    def add_to_inbox(self, title: str, url: str, reason: str, item_type: str = 'recommended_reading'):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO inbox (title, url, recommendation_reason, type) VALUES (?, ?, ?, ?)",
                (title, url, reason, item_type)
            )

    def get_inbox(self) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM inbox WHERE status = 'pending'").fetchall()
            return [dict(r) for r in rows]

    def search(self, query_text: str, layer: Optional[int] = None, category: Optional[str] = None) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            # 1. Try keyword search
            sql = "SELECT * FROM chunks WHERE content LIKE ?"
            params: List[Any] = [f"%{query_text}%"]
            if layer:
                sql += " AND layer = ?"
                params.append(layer)
            if category:
                sql += " AND category = ?"
                params.append(category)
            
            rows = conn.execute(sql, params).fetchall()
            
            # 2. Fallback: If no results and category is provided, return top entries for that category
            if not rows and category:
                sql = "SELECT * FROM chunks WHERE category = ?"
                params = [category]
                if layer:
                    sql += " AND layer = ?"
                    params.append(layer)
                sql += " LIMIT 5"
                rows = conn.execute(sql, params).fetchall()
                
            return [dict(r) for r in rows]
