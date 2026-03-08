import os
import sqlite3
import sqlite_vec
import struct
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
import json
import logging

from lib.ollama_client import embed
from lib.llm import ask
from lib.event_bus import emit

@dataclass
class SearchResult:
    content: str
    metadata: Dict[str, Any]
    score: float

class SemanticMemory:
    """sqlite-vec powered vector store. Drop-in upgrade to existing knowledge.db."""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_dir = Path(os.environ.get("JARVIS_ROOT", Path(__file__).resolve().parent.parent))
            self.db_path = str(base_dir / "data" / "knowledge.db")
        else:
            self.db_path = db_path
            
        self._init_db()
        
    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            # Drop legacy BLOB approach table if starting fresh (we'll migrate otherwise)
            # Create our vector table and metadata linked by rowid
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0(
                    embedding float[768]
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunk_metadata (
                    rowid    INTEGER PRIMARY KEY,
                    layer    INTEGER NOT NULL,
                    category TEXT,
                    source   TEXT,
                    content  TEXT NOT NULL,
                    ts       TEXT NOT NULL
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    chunk_rowid INTEGER,
                    subject     TEXT NOT NULL,
                    relation    TEXT NOT NULL,
                    object      TEXT NOT NULL,
                    FOREIGN KEY (chunk_rowid) REFERENCES chunk_metadata(rowid) ON DELETE CASCADE
                );
            """)
            conn.commit()

    async def _extract_entities(self, content: str) -> List[Tuple[str, str, str]]:
        """Use language model to extract knowledge graph triples."""
        prompt = f"""Extract 1 to 5 factual relationships from the text below.
Format strict JSON list of lists: [["Subject", "Relation", "Object"]].
Keep entities short. No conversational text.
Text: {content}"""
        try:
            # FIX: ask() is now async/returns coroutine
            res_obj = await ask(task="analyze", prompt=prompt, thinking=False)
            res_text = res_obj.content if hasattr(res_obj, "content") else str(res_obj)
            if not isinstance(res_text, str):
                return []
            res_text = res_text.strip()
            
            # Very basic JSON array extraction since LLMs can wrap in markdown ```json
            start = res_text.find('[')
            end = res_text.rfind(']') + 1
            if start != -1 and end != 0:
                clean_json = res_text[start:end]
                triples = json.loads(clean_json)
                valid_triples = []
                for t in triples:
                    if isinstance(t, list) and len(t) == 3:
                        valid_triples.append((str(t[0]), str(t[1]), str(t[2])))
                return valid_triples
        except Exception as e:
            emit('semantic_memory', 'extraction_failed', {'error': str(e)})
            
        return []

    def _chunk_text(self, text: str, max_chars: int = 5000, overlap: int = 500) -> List[str]:
        """Simple recursive-style char chunking."""
        if len(text) <= max_chars:
            return [text]
        
        chunks = []
        start = 0
        while start < len(text):
            end = start + max_chars
            # Try to find a double newline or newline or space to break at
            if end < len(text):
                found_break = False
                for b in ["\n\n", "\n", ". ", " "]:
                    idx = text.rfind(b, start + max_chars // 2, end)
                    if idx != -1:
                        end = idx + len(b)
                        found_break = True
                        break
            
            chunks.append(text[start:end].strip())
            if end >= len(text):
                break
            start = end - overlap
        return chunks

    async def ingest(self, content: str, metadata: dict, layer: int = 1, category: Optional[str] = None) -> None:
        """Embed text and store in sqlite-vec virtual table. Automatically chunks large content."""
        chunks = self._chunk_text(content)
        
        if len(chunks) > 1:
            print(f"[SemanticMemory] Splitting large content into {len(chunks)} chunks...")
            
        for i, chunk in enumerate(chunks):
            try:
                # Generate embedding
                # FIX: embed() is now async/returns coroutine
                vector = await embed("embed", chunk)
                if not vector:
                    emit('semantic_memory', 'ingest_failed', {'reason': 'Empty embedding returned'})
                    continue
                    
                vector_bytes = struct.pack(f"<{len(vector)}f", *vector)
                
                source = metadata.get("source", "unknown")
                ts = datetime.utcnow().isoformat()
                
                # Add chunk index to metadata if multiple
                chunk_meta = {**metadata}
                if len(chunks) > 1:
                    chunk_meta["chunk"] = i
                    chunk_meta["total_chunks"] = len(chunks)
                
                with self._get_connection() as conn:
                    cursor = conn.execute(
                        "INSERT INTO chunk_metadata (layer, category, source, content, ts) VALUES (?, ?, ?, ?, ?)",
                        (layer, category, source, chunk, ts)
                    )
                    rowid = cursor.lastrowid
                    
                    conn.execute(
                        "INSERT INTO vec_chunks (rowid, embedding) VALUES (?, ?)",
                        (rowid, vector_bytes)
                    )
                    
                    # Entity extraction only on smaller chunks is better anyway
                    triples = await self._extract_entities(chunk)
                    if triples:
                        for item in triples:
                            sub = str(item[0])[:100]
                            rel = str(item[1])[:50]
                            obj = str(item[2])[:100]
                            conn.execute(
                                "INSERT INTO entities (chunk_rowid, subject, relation, object) VALUES (?, ?, ?, ?)",
                                (rowid, sub, rel, obj)
                            )
                    conn.commit()
                
                emit('semantic_memory', 'ingested', {'layer': layer, 'category': category, 'chunk': i})
                
            except Exception as e:
                emit('semantic_memory', 'ingest_error', {'error': str(e), 'chunk': i})
                print(f"[SemanticMemory] Error ingesting chunk {i}: {e}")

    async def query(self, query_text: str, k: int = 5, category: Optional[str] = None, categories: Optional[List[str]] = None, use_hybrid: bool = True) -> List[SearchResult]:
        """
        Native vector similarity search utilizing the fast vec0 backend.
        """
        try:
            # FIX: embed() is now async/returns coroutine
            query_vector = await embed("embed", query_text)
            if not query_vector:
                return []
                
            vector_bytes = struct.pack(f"<{len(query_vector)}f", *query_vector)
            
            with self._get_connection() as conn:
                # Native KNN search via sqlite-vec
                # FIX: If category filter is used, we must search deeper (larger k) 
                # to ensure we don't miss matches after filtering.
                search_k = k * 10 if (category or categories) else k
                
                if categories:
                    placeholders = ",".join("?" for _ in categories)
                    sql = f"""
                        SELECT m.content, m.layer, m.category, m.source, v.distance 
                        FROM vec_chunks v
                        JOIN chunk_metadata m ON v.rowid = m.rowid
                        WHERE v.embedding MATCH ? AND v.k = ? AND m.category IN ({placeholders})
                        ORDER BY v.distance ASC
                        LIMIT ?
                    """
                    params = (vector_bytes, search_k) + tuple(categories) + (k,)
                elif category:
                    sql = """
                        SELECT m.content, m.layer, m.category, m.source, v.distance 
                        FROM vec_chunks v
                        JOIN chunk_metadata m ON v.rowid = m.rowid
                        WHERE v.embedding MATCH ? AND v.k = ? AND m.category = ?
                        ORDER BY v.distance ASC
                        LIMIT ?
                    """
                    params = (vector_bytes, search_k, category, k)
                else:
                    sql = """
                        SELECT m.content, m.layer, m.category, m.source, v.distance 
                        FROM vec_chunks v
                        JOIN chunk_metadata m ON v.rowid = m.rowid
                        WHERE v.embedding MATCH ? AND v.k = ?
                        ORDER BY v.distance ASC
                    """
                    params = (vector_bytes, k)
                    
                rows = conn.execute(sql, params).fetchall()
                
                results = []
                for row in rows:
                    content = row['content']
                    metadata = {'layer': row['layer'], 'category': row['category'], 'source': row['source']}
                    # Distance is typically cosine distance in nomic models. Score is similarity.
                    similarity = max(0.0, 1.0 - row['distance'])
                    results.append(SearchResult(content=content, metadata=metadata, score=similarity))
                    
                return results

        except Exception as e:
            emit('semantic_memory', 'query_error', {'error': str(e)})
            return []

    def delete_by_source(self, source: str) -> None:
        """Remove all chunks and vectors associated with a specific source."""
        with self._get_connection() as conn:
            # Get rowids to delete
            cursor = conn.execute("SELECT rowid FROM chunk_metadata WHERE source = ?", (source,))
            rowids = [row['rowid'] for row in cursor.fetchall()]
            
            if rowids:
                placeholders = ",".join("?" for _ in rowids)
                conn.execute(f"DELETE FROM chunk_metadata WHERE rowid IN ({placeholders})", tuple(rowids))
                conn.execute(f"DELETE FROM vec_chunks WHERE rowid IN ({placeholders})", tuple(rowids))
                conn.commit()
                emit('semantic_memory', 'deleted', {'source': source, 'count': len(rowids)})

    def migrate_from_blob(self) -> None:
        """One-time migration of existing BLOB embeddings to sqlite-vec."""
        import numpy as np
        
        with self._get_connection() as conn:
            # Check if old table exists
            table_exists = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='chunks'"
            ).fetchone()
            
            if not table_exists:
                print("No legacy 'chunks' table found. Migration not needed.")
                return
                
            # Fetch all old records
            print("Fetching legacy BLOB records...")
            cursor = conn.execute("SELECT id, layer, category, source_url, content, embedding, last_updated FROM chunks")
            rows = cursor.fetchall()
            
            if not rows:
                print("Legacy 'chunks' table is empty. Migration complete.")
                return
                
            print(f"Migrating {len(rows)} records to sqlite-vec format...")
            
            migrated_count = 0
            for row in rows:
                embedding_blob = row['embedding']
                if not embedding_blob:
                    continue
                    
                # Decode original BLOB to get the list of floats
                try:
                    vector = np.frombuffer(embedding_blob, dtype=np.float32).tolist()
                    vector_bytes = struct.pack(f"<{len(vector)}f", *vector) # Fast sqlite-vec packing
                except Exception as e:
                    print(f"  Warning: Failed to decode blob for ID {row['id']}: {e}")
                    continue
                
                # Insert metadata
                try:
                    meta_cursor = conn.execute(
                        "INSERT INTO chunk_metadata (rowid, layer, category, source, content, ts) VALUES (?, ?, ?, ?, ?, ?)",
                        (row['id'], row['layer'], row['category'], row['source_url'], row['content'], row['last_updated'])
                    )
                    
                    # Insert vector
                    conn.execute(
                        "INSERT INTO vec_chunks (rowid, embedding) VALUES (?, ?)",
                        (row['id'], vector_bytes)
                    )
                    migrated_count += 1
                except sqlite3.IntegrityError:
                    print(f"  Skipping row {row['id']} (already migrated)")
                    continue
                    
            conn.commit()
            print(f"Migration complete! {migrated_count} vectors successfully transferred to sqlite-vec.")
