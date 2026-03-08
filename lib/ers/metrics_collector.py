# lib/ers/metrics_collector.py
import asyncio
import aiosqlite
import json
from pathlib import Path
from typing import Any

DB_PATH = Path.home() / ".jarvis" / "metrics.db"

class MetricsCollector:
    """Tracks performance, token usage, and tool success/failure for ERS chains."""
    
    def __init__(self, db_file: Path | str = DB_PATH):
        self.db_file = Path(db_file)
        self.db_file.parent.mkdir(parents=True, exist_ok=True)
        self._conn: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize the SQLite database and create tables if they don't exist."""
        async with self._lock:
            if not self._conn:
                self._conn = await aiosqlite.connect(self.db_file)
                await self._conn.execute('''
                    CREATE TABLE IF NOT EXISTS chain_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chain_id TEXT NOT NULL,
                        execution_id TEXT NOT NULL,
                        start_time REAL,
                        end_time REAL,
                        latency REAL,
                        status TEXT,
                        total_tokens INTEGER DEFAULT 0
                    )
                ''')
                await self._conn.execute('''
                    CREATE TABLE IF NOT EXISTS step_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        execution_id TEXT NOT NULL,
                        step_id TEXT NOT NULL,
                        tool TEXT,
                        start_time REAL,
                        end_time REAL,
                        latency REAL,
                        status TEXT,
                        tokens_used INTEGER DEFAULT 0,
                        correction_attempts INTEGER DEFAULT 0,
                        diffs TEXT
                    )
                ''')
                await self._conn.commit()

    async def close(self) -> None:
        """Close the database connection."""
        async with self._lock:
            if self._conn:
                await self._conn.close()
                self._conn = None

    async def log_chain_start(self, chain_id: str, execution_id: str, start_time: float) -> None:
        """Log the start of a chain execution."""
        async with self._lock:
            if self._conn:
                await self._conn.execute('''
                    INSERT INTO chain_metrics (chain_id, execution_id, start_time, status)
                    VALUES (?, ?, ?, ?)
                ''', (chain_id, execution_id, start_time, 'running'))
                await self._conn.commit()

    async def log_chain_end(self, execution_id: str, end_time: float, status: str, total_tokens: int = 0) -> None:
        """Log the completion or failure of a chain execution."""
        async with self._lock:
            if self._conn:
                await self._conn.execute('''
                    UPDATE chain_metrics
                    SET end_time = ?, latency = ? - start_time, status = ?, total_tokens = ?
                    WHERE execution_id = ?
                ''', (end_time, end_time, status, total_tokens, execution_id))
                await self._conn.commit()
    
    async def log_step(
        self, execution_id: str, step_id: str, tool: str, start_time: float,
        end_time: float, status: str, tokens_used: int = 0,
        correction_attempts: int = 0, diffs: list[Any] | dict[str, Any] | None = None
    ) -> None:
        """Log the outcome of an individual step within a chain."""
        async with self._lock:
            if self._conn:
                latency = end_time - start_time
                diffs_str = json.dumps(diffs) if diffs else None
                await self._conn.execute('''
                    INSERT INTO step_metrics
                    (execution_id, step_id, tool, start_time, end_time, latency, status, tokens_used, correction_attempts, diffs)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (execution_id, step_id, tool, start_time, end_time, latency, status, tokens_used, correction_attempts, diffs_str))
                await self._conn.commit()
                
    async def generate_report(self, limit: int = 50) -> list[dict[str, Any]]:
        """Generate a summarized report of recent chain executions."""
        async with self._lock:
            if not self._conn:
                return []
            
            async with self._conn.execute('''
                SELECT execution_id, chain_id, latency, status, total_tokens, start_time, end_time
                FROM chain_metrics
                ORDER BY id DESC
                LIMIT ?
            ''', (limit,)) as cursor:
                rows = await cursor.fetchall()
            
            report = []
            for row in rows:
                execution_id, chain_id, latency, status, total_tokens, start_time, end_time = row
                
                async with self._conn.execute('''
                    SELECT step_id, tool, latency, status, tokens_used, correction_attempts
                    FROM step_metrics
                    WHERE execution_id = ?
                ''', (execution_id,)) as step_cursor:
                    step_rows = await step_cursor.fetchall()
                    
                steps = [{
                    "step_id": s[0],
                    "tool": s[1],
                    "latency": s[2],
                    "status": s[3],
                    "tokens_used": s[4],
                    "correction_attempts": s[5]
                } for s in step_rows]
                
                report.append({
                    "execution_id": execution_id,
                    "chain_id": chain_id,
                    "latency": latency,
                    "status": status,
                    "total_tokens": total_tokens,
                    "start_time": start_time,
                    "end_time": end_time,
                    "steps": steps
                })
                
            return report
