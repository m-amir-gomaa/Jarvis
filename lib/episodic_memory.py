import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

# /THE_VAULT/jarvis/lib/episodic_memory.py

DB_PATH = Path("/THE_VAULT/jarvis/logs/events.db")

def get_recent_events(limit: int = 20, source: Optional[str] = None) -> List[Dict[str, Any]]:
    if not DB_PATH.exists():
        return []
    
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    query = "SELECT ts, source, event, details, level FROM events"
    params: List[Any] = []
    
    if source:
        query += " WHERE source = ?"
        params.append(source)
    
    query += " ORDER BY ts DESC LIMIT ?"
    params.append(limit)
    
    rows = con.execute(query, params).fetchall()
    con.close()
    
    return [dict(r) for r in rows]

def search_memory(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    if not DB_PATH.exists():
        return []
        
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    # Simple keyword search for now
    rows = con.execute(
        "SELECT ts, source, event, details FROM events WHERE details LIKE ? OR event LIKE ? ORDER BY ts DESC LIMIT ?",
        (f"%{query}%", f"%{query}%", limit)
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]

def get_session_context() -> str:
    """Aggregates the most relevant recent events into a context string."""
    events = get_recent_events(limit=5)
    if not events:
        return "No recent episodic memory found."
        
    parts = ["## Recent Episodic Memory"]
    for e in reversed(events):
        parts.append(f"- [{e['ts']}] {e['source']}: {e['event']} ({e['details'][:100]}...)")
    return "\n".join(parts)
