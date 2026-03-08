#!/usr/bin/env python3
"""
benchmarks/system_analysis/check_knowledge.py
Real knowledge base health check — queries actual SQLite databases.
"""
import json
import sqlite3
from pathlib import Path

VAULT = Path("/THE_VAULT/jarvis")


def _db_stats(db_path: Path) -> dict:
    if not db_path.exists():
        return {"exists": False}
    size_mb = round(db_path.stat().st_size / 1024 / 1024, 2)
    stats = {"exists": True, "size_mb": size_mb, "tables": {}}
    try:
        with sqlite3.connect(str(db_path)) as conn:
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            for table in tables:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                stats["tables"][table] = count
    except Exception as e:
        stats["error"] = str(e)
    return stats


def check_knowledge() -> dict:
    result = {}

    # Main knowledge database
    knowledge_db = VAULT / "databases" / "knowledge.db"
    result["knowledge_db"] = _db_stats(knowledge_db)

    # Per-layer chunk counts
    if result["knowledge_db"].get("exists") and "chunks" in result["knowledge_db"].get("tables", {}):
        try:
            with sqlite3.connect(str(knowledge_db)) as conn:
                # Category distribution
                cats = conn.execute(
                    "SELECT category, COUNT(*) as cnt FROM chunks GROUP BY category ORDER BY cnt DESC LIMIT 20"
                ).fetchall()
                result["top_categories"] = [{"category": r[0], "chunks": r[1]} for r in cats]

                # Inbox queue
                try:
                    inbox_count = conn.execute("SELECT COUNT(*) FROM inbox").fetchone()[0]
                    result["inbox_pending"] = inbox_count
                except Exception:
                    result["inbox_pending"] = "table_missing"

                # Last ingest timestamp
                try:
                    last_ts = conn.execute(
                        "SELECT MAX(created_at) FROM chunks"
                    ).fetchone()[0]
                    result["last_ingest_at"] = last_ts
                except Exception:
                    result["last_ingest_at"] = "unknown"

                # Orphan detection: chunks without embeddings (if embeddings column exists)
                try:
                    orphans = conn.execute(
                        "SELECT COUNT(*) FROM chunks WHERE embedding IS NULL OR embedding = ''"
                    ).fetchone()[0]
                    result["chunks_without_embeddings"] = orphans
                except Exception:
                    result["chunks_without_embeddings"] = "n/a"
        except Exception as e:
            result["knowledge_db"]["query_error"] = str(e)

    # Security audit database
    audit_db = VAULT / "databases" / "security_audit.db"
    result["security_audit_db"] = _db_stats(audit_db)

    # Associations (codebase → knowledge category)
    assoc_db = VAULT / "databases" / "associations.db"
    if assoc_db.exists():
        result["associations_db"] = _db_stats(assoc_db)
        try:
            with sqlite3.connect(str(assoc_db)) as conn:
                assocs = conn.execute("SELECT path, category FROM associations").fetchall()
                result["active_associations"] = [{"path": r[0], "category": r[1]} for r in assocs]
        except Exception:
            result["active_associations"] = []
    else:
        result["associations_db"] = {"exists": False}

    return result


if __name__ == "__main__":
    data = check_knowledge()
    print(json.dumps(data, indent=2))
