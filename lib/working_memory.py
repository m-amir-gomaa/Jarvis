import os
import sqlite3
import uuid
from typing import Optional
from datetime import datetime, timezone
from pathlib import Path

# /home/qwerty/NixOSenv/Jarvis/lib/working_memory.py

JARVIS_ROOT = Path(os.environ.get("JARVIS_ROOT", Path(__file__).resolve().parent.parent))
DB_PATH = JARVIS_ROOT / "data" / "sessions.db"

class WorkingMemory:
    """Persists conversation turns across CLI sessions in data/sessions.db."""
    
    def __init__(self):
        os.makedirs(DB_PATH.parent, exist_ok=True)
        self._init_db()
        
    def _init_db(self):
        with sqlite3.connect(DB_PATH) as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS turns (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    ts         TEXT NOT NULL,
                    role       TEXT NOT NULL,   -- 'user' | 'assistant' | 'system'
                    content    TEXT NOT NULL,
                    tokens     INTEGER          -- estimated token count
                );
                CREATE INDEX IF NOT EXISTS idx_session_ts ON turns(session_id, ts);
            ''')
            
    def _get_default_session(self) -> str:
        # Defaults to today's date YYYY-MM-DD
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def load_session(self, session_id: Optional[str] = None) -> list[dict]:
        """Load last N turns for the session. If no session_id, use today's."""
        sid = session_id or self._get_default_session()
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                "SELECT role, content FROM turns WHERE session_id = ? ORDER BY ts ASC",
                (sid,)
            ).fetchall()
        
        return [{"role": r[0], "content": r[1]} for r in rows]

    def save_turn(self, role: str, content: str, session_id: Optional[str] = None) -> None:
        """Append a single turn (user or assistant) to the session."""
        sid = session_id or self._get_default_session()
        ts = datetime.now(timezone.utc).isoformat()
        tokens = len(content) // 4  # rough heuristic
        
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO turns (session_id, ts, role, content, tokens) VALUES (?, ?, ?, ?, ?)",
                (sid, ts, role, content, tokens)
            )

    def get_context_messages(self, max_turns: int = 10, session_id: Optional[str] = None) -> list[dict]:
        """Return last max_turns as [{'role': ..., 'content': ...}] for injection."""
        # Grab all rows, then tail N
        msgs = self.load_session(session_id)
        if len(msgs) > max_turns:
            return msgs[-max_turns:]
        return msgs

    def summarize_and_compress(self) -> None:
        """If session > 6000 tokens, summarize old turns, keep last 4 verbatim."""
        pass # Optional for now, will implement if requested

    def new_session(self) -> str:
        """Start a fresh session, return new session_id."""
        return str(uuid.uuid4())

    def clear(self, session_id: Optional[str] = None) -> None:
        """Delete current session's turns (for 'jarvis forget' command)."""
        sid = session_id or self._get_default_session()
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM turns WHERE session_id = ?", (sid,))
            
    def list_sessions(self) -> list[dict]:
        """Returns aggregated session info."""
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute('''
                SELECT session_id, COUNT(*) as turns, SUM(tokens) as total_tokens, MAX(ts) as last_active
                FROM turns 
                GROUP BY session_id 
                ORDER BY last_active DESC 
                LIMIT 20
            ''').fetchall()
            
        return [
            {
                "session_id": r[0],
                "turns": r[1],
                "tokens": r[2] or 0,
                "last_active": r[3]
            } for r in rows
        ]
