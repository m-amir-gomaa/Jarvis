import faiss
import numpy as np
import aiosqlite
import asyncio
import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class FaissIndexManager:
    """
    Manages persistent FAISS vector store with an aiosqlite metadata companion.
    Thread-safe FAISS operations via asyncio Locks and run_in_executor.
    """
    def __init__(self, 
                 index_dir: str = "~/.jarvis/index",
                 dimension: int = 768): # nomic-embed-text generates 768 dimensions
        
        self.index_dir = Path(index_dir).expanduser()
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        self.faiss_path = self.index_dir / "faiss.bin"
        self.db_path = self.index_dir / "metadata.db"
        self.dimension = dimension
        
        self.index: Optional[faiss.Index] = None
        
        # We need an asyncio Lock to prevent concurrent modification of the FAISS index
        self._faiss_lock = asyncio.Lock()
        
    async def initialize(self):
        """Must be called before using the manager."""
        await self._init_db()
        await self._load_or_create_faiss()

    async def _init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS chunk_metadata (
                    id INTEGER PRIMARY KEY,
                    chunk_id TEXT UNIQUE,
                    source_path TEXT,
                    chunk_type TEXT,
                    content TEXT,
                    start_line INTEGER,
                    end_line INTEGER,
                    extra_meta TEXT
                )
            ''')
            # Create indexing for faster queries
            await db.execute('CREATE INDEX IF NOT EXISTS idx_source ON chunk_metadata(source_path)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_type ON chunk_metadata(chunk_type)')
            await db.commit()

    async def _load_or_create_faiss(self):
        async with self._faiss_lock:
            if self.faiss_path.exists():
                logger.info(f"Loading existing FAISS index from {self.faiss_path}")
                self.index = await asyncio.to_thread(faiss.read_index, str(self.faiss_path))
            else:
                logger.info(f"Creating new FAISS IndexFlatIP (dim={self.dimension})")
                # Using Inner Product (Cosine Similarity works if vectors are normalized)
                # faiss.IndexIDMap to allow integer custom IDs matching our SQLite autoincrement
                base_index = faiss.IndexFlatIP(self.dimension)
                self.index = faiss.IndexIDMap(base_index)
                
    async def _save_faiss(self):
        if self.index is not None:
            await asyncio.to_thread(faiss.write_index, self.index, str(self.faiss_path))

    async def add(self, chunk_id: str, source_path: str, chunk_type: str, content: str, 
                  embedding: List[float], start_line: int = 0, end_line: int = 0, 
                  extra_meta: Optional[Dict[str, Any]] = None):
        """Add a chunk and its vector. Vectors should be L2 normalized before adding for IP->Cosine to hold."""
        if self.index is None:
            raise RuntimeError("FaissIndexManager not initialized.")
            
        extra_str = json.dumps(extra_meta or {})
        vec = np.array([embedding], dtype=np.float32)
        # Normalize vector for Cosine Similarity inside IndexFlatIP
        faiss.normalize_L2(vec)

        async with self._faiss_lock:
            async with aiosqlite.connect(self.db_path) as db:
                # Insert into DB and get the auto-increment ID to use in FAISS IndexIDMap
                cursor = await db.execute('''
                    INSERT INTO chunk_metadata 
                    (chunk_id, source_path, chunk_type, content, start_line, end_line, extra_meta)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(chunk_id) DO UPDATE SET
                    source_path=excluded.source_path,
                    chunk_type=excluded.chunk_type,
                    content=excluded.content,
                    start_line=excluded.start_line,
                    end_line=excluded.end_line,
                    extra_meta=excluded.extra_meta
                ''', (chunk_id, source_path, chunk_type, content, start_line, end_line, extra_str))
                
                # Retrieve the actual rowid for the inserted/updated chunk
                cursor = await db.execute('SELECT id FROM chunk_metadata WHERE chunk_id = ?', (chunk_id,))
                row = await cursor.fetchone()
                db_id = row[0]
                await db.commit()

            # Now add or update in FAISS
            # FAISS IndexIDMap does not support updating in place easily, so typically we delete first if it's an update.
            await asyncio.to_thread(self.index.remove_ids, np.array([db_id], dtype=np.int64))
            await asyncio.to_thread(self.index.add_with_ids, vec, np.array([db_id], dtype=np.int64))
            
            # Immediately save after structural change
            await self._save_faiss()

    async def search(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """Search similar vectors and return metadata."""
        if self.index is None or self.index.ntotal == 0:
            return []

        vec = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(vec)

        async with self._faiss_lock:
            # Perform search in a thread since it can block
            scores, ids = await asyncio.to_thread(self.index.search, vec, top_k)
            
        results = []
        valid_ids = [int(idx) for idx in ids[0] if idx != -1]
        if not valid_ids:
            return results

        async with aiosqlite.connect(self.db_path) as db:
            # Use dynamically formatted query for IN clause safely mapping IDs
            placeholders = ','.join('?' for _ in valid_ids)
            cursor = await db.execute(
                f'SELECT id, chunk_id, source_path, chunk_type, content, start_line, end_line, extra_meta FROM chunk_metadata WHERE id IN ({placeholders})',
                valid_ids
            )
            rows = await cursor.fetchall()
            
            # Map row id to data for ordered attachment
            row_map = {}
            for row in rows:
                meta = json.loads(row[7]) if row[7] else {}
                row_map[row[0]] = {
                    "chunk_id": row[1],
                    "source_path": row[2],
                    "chunk_type": row[3],
                    "content": row[4],
                    "start_line": row[5],
                    "end_line": row[6],
                    "extra_meta": meta
                }
                
            # Combine scores and preserve FAISS ordering
            for score, db_id in zip(scores[0], ids[0]):
                if db_id != -1 and db_id in row_map:
                    item = row_map[db_id].copy()
                    item["score"] = float(score)
                    results.append(item)
                    
        return results

    async def delete_by_source(self, source_path: str):
        """Remove all chunks and related vectors for a specific file/source."""
        if self.index is None:
            return
            
        async with self._faiss_lock:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('SELECT id FROM chunk_metadata WHERE source_path = ?', (source_path,))
                rows = await cursor.fetchall()
                if not rows:
                    return
                # Get the integer ids to remove
                ids_to_remove = [row[0] for row in rows]
                
                # Delete from DB
                await db.execute('DELETE FROM chunk_metadata WHERE source_path = ?', (source_path,))
                await db.commit()

            # Remove from FAISS
            await asyncio.to_thread(self.index.remove_ids, np.array(ids_to_remove, dtype=np.int64))
            await self._save_faiss()

    async def rebuild(self):
        """Completely drops and recreates the index and db."""
        async with self._faiss_lock:
            self.index = None
            if self.db_path.exists():
                self.db_path.unlink()
            if self.faiss_path.exists():
                self.faiss_path.unlink()
                
        await self.initialize()

# Alias for backwards-compatibility with imports that use the uppercase name
FAISSIndexManager = FaissIndexManager
