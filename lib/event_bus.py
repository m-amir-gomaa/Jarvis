import sqlite3
import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Optional

# /THE_VAULT/jarvis/lib/event_bus.py

DB_PATH = '/THE_VAULT/jarvis/logs/events.db'

def _init_db():
    """Initializes the events database if it doesn't exist."""
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            source TEXT NOT NULL,
            event TEXT NOT NULL,
            details TEXT,
            level TEXT NOT NULL
        )
    ''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_ts ON events(ts)')
    conn.commit()
    conn.close()

def emit(source: str, event: str, details: Optional[Dict] = None, level: str = 'INFO'):
    """
    Emits an event to the events.db.
    Example: emit('ingest', 'completed', {'file': 'paper.pdf', 'chunks': 42})
    """
    if not os.path.exists(DB_PATH):
        _init_db()
        
    ts = datetime.now(timezone.utc).isoformat()
    details_json = json.dumps(details or {})
    
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            'INSERT INTO events (ts, source, event, details, level) VALUES (?, ?, ?, ?, ?)',
            (ts, source, event, details_json, level)
        )
        conn.commit()
    finally:
        conn.close()

def query_today() -> List[Dict]:
    """
    Queries events that occurred today (UTC).
    """
    if not os.path.exists(DB_PATH):
        return []
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        # queries for the last 24 hours of events
        rows = conn.execute(
            "SELECT source, event, details, ts, level FROM events WHERE ts > datetime('now', '-1 day') ORDER BY ts DESC"
        ).fetchall()
        
        return [
            {
                'source': r['source'],
                'event': r['event'],
                'details': json.loads(r['details']),
                'ts': r['ts'],
                'level': r['level']
            } for r in rows
        ]
    finally:
        conn.close()

if __name__ == "__main__":
    # Test block
    _init_db()
    emit('test', 'startup', {'msg': 'Event bus initialized'})
    events = query_today()
    print(f"Recorded {len(events)} events today.")
    for e in events:
        print(f"[{e['ts']}] {e['source']}.{e['event']}: {e['details']}")
