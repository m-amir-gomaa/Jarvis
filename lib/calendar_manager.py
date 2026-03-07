#!/usr/bin/env python3
"""
Calendar & Task Manager (Phase 7.5)
/home/qwerty/NixOSenv/Jarvis/lib/calendar_manager.py

Simple SQLite-based calendar and task management for Jarvis.
"""

import sqlite3
import os
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

class CalendarManager:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_dir = Path(os.environ.get("JARVIS_ROOT", Path(__file__).resolve().parent.parent))
            self.db_path = str(base_dir / "data" / "calendar.db")
        else:
            self.db_path = db_path
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            # Events table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    start_ts TEXT NOT NULL,
                    end_ts TEXT,
                    description TEXT,
                    location TEXT,
                    category TEXT DEFAULT 'general'
                )
            """)
            # Tasks table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    due_ts TEXT,
                    priority INTEGER DEFAULT 2,
                    status TEXT DEFAULT 'pending',
                    description TEXT,
                    created_ts TEXT NOT NULL
                )
            """)
            conn.commit()

    def add_event(self, title: str, start_ts: str, end_ts: Optional[str] = None, description: str = ""):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO events (title, start_ts, end_ts, description) VALUES (?, ?, ?, ?)",
                (title, start_ts, end_ts, description)
            )

    def list_events(self, days: int = 7) -> List[Dict]:
        now = datetime.now(timezone.utc).isoformat()
        future = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM events WHERE start_ts >= ? AND start_ts <= ? ORDER BY start_ts ASC",
                (now, future)
            ).fetchall()
            return [dict(r) for r in rows]

    def add_task(self, title: str, due_ts: Optional[str] = None, priority: int = 2, description: str = ""):
        created = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO tasks (title, due_ts, priority, description, created_ts) VALUES (?, ?, ?, ?, ?)",
                (title, due_ts, priority, description, created)
            )

    def list_tasks(self, status: str = 'pending') -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM tasks WHERE status = ? ORDER BY priority DESC, created_ts ASC",
                (status,)
            ).fetchall()
            return [dict(r) for r in rows]

    def complete_task(self, task_id: int):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE tasks SET status = 'completed' WHERE id = ?", (task_id,))

if __name__ == "__main__":
    cm = CalendarManager()
    cm.add_task("Test Task", priority=1)
    print("Tasks:", cm.list_tasks())
