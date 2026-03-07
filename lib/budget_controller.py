import os
import sqlite3
from typing import Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import tomllib
from pathlib import Path

# /home/qwerty/NixOSenv/Jarvis/lib/budget_controller.py

JARVIS_ROOT = Path(os.environ.get("JARVIS_ROOT", Path(__file__).resolve().parent.parent))
_VAULT_ROOT = Path(os.environ.get("VAULT_ROOT", "/THE_VAULT/jarvis"))
DB_PATH = _VAULT_ROOT / "databases" / "security_audit.db"
CONFIG_PATH = JARVIS_ROOT / "config" / "budget.toml"

@dataclass
class BudgetDecision:
    allowed: bool
    reason: str
    fallback: str

class BudgetController:
    def __init__(self):
        os.makedirs(DB_PATH.parent, exist_ok=True)
        self._init_db()
        self.config = self._load_config()

    def _init_db(self):
        with sqlite3.connect(DB_PATH) as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS api_usage (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts            TEXT NOT NULL,
                    model         TEXT NOT NULL,
                    task          TEXT NOT NULL,
                    prompt_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    cost_usd      REAL NOT NULL,
                    session_id    TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_ts ON api_usage(ts);
                CREATE INDEX IF NOT EXISTS idx_session ON api_usage(session_id);

                CREATE TABLE IF NOT EXISTS sessions (
                    session_id    TEXT PRIMARY KEY,
                    started_at    TEXT NOT NULL,
                    ended_at      TEXT,
                    total_tokens  INTEGER DEFAULT 0,
                    total_cost    REAL DEFAULT 0.0,
                    status        TEXT DEFAULT 'active'
                );
            ''')

    def _load_config(self) -> dict:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "rb") as f:
                return tomllib.load(f)
        return {
            "limits": {
                "daily_tokens": 200000,
                "daily_cost_usd": 2.00,
                "monthly_cost_usd": 30.00,
                "warning_threshold": 0.80
            },
            "per_task_limits": {
                "research": 8000,
                "fix": 12000,
                "reason": 16000,
                "chat": 6000,
                "default": 4000
            },
            "agent_loop": {
                "max_steps": 8,
                "max_tokens_per_session": 40000
            },
            "model_costs": {
                "claude-sonnet-4-5": {"input": 0.003, "output": 0.015},
                "claude-opus-4-5": {"input": 0.015, "output": 0.075},
                "gpt-4o": {"input": 0.005, "output": 0.015}
            }
        }

    def check_and_reserve(self, task: str, estimated_tokens: int) -> BudgetDecision:
        """
        Returns BudgetDecision(allowed=bool, reason=str, fallback=str).
        Checks: (1) daily token limit, (2) per-task limit, (3) monthly cost.
        MUST be called before every cloud API request.
        """
        task_limit = self.config["per_task_limits"].get(task, self.config["per_task_limits"]["default"])
        if estimated_tokens > task_limit:
            return BudgetDecision(allowed=False, reason=f"Estimated tokens ({estimated_tokens}) exceed per-task limit ({task_limit})", fallback="local")

        summary = self.get_daily_summary()
        limits = self.config["limits"]

        if summary["tokens_used"] + estimated_tokens > limits["daily_tokens"]:
            return BudgetDecision(allowed=False, reason="Daily token limit exhausted", fallback="local")

        if summary["cost_usd"] > limits["daily_cost_usd"]:
            return BudgetDecision(allowed=False, reason="Daily USD cost limit exhausted", fallback="local")
        
        # Monthly check (simplistic, based on last 30 days or current month)
        monthly_cost = self._get_monthly_cost()
        if monthly_cost > limits["monthly_cost_usd"]:
            return BudgetDecision(allowed=False, reason="Monthly USD cost limit exhausted", fallback="local")

        return BudgetDecision(allowed=True, reason="Within budget", fallback="")

    def record_usage(self, model: str, task: str,
                     prompt_tokens: int, output_tokens: int,
                     session_id: Optional[str] = None) -> None:
        """Writes to data/api_usage.db. Calculates cost from budget.toml rates."""
        cost_rates = self.config["model_costs"].get(model, {"input": 0.0, "output": 0.0})
        cost_usd = (prompt_tokens * cost_rates["input"] / 1000.0) + (output_tokens * cost_rates["output"] / 1000.0)

        ts = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute('''
                INSERT INTO api_usage (ts, model, task, prompt_tokens, output_tokens, cost_usd, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (ts, model, task, prompt_tokens, output_tokens, cost_usd, session_id))

            if session_id:
                conn.execute('''
                    UPDATE sessions
                    SET total_tokens = total_tokens + ?,
                        total_cost = total_cost + ?
                    WHERE session_id = ?
                ''', (prompt_tokens + output_tokens, cost_usd, session_id))

    def estimate_tokens(self, text: str) -> int:
        """Fast pre-flight estimate: len(text) // 4. No model call needed."""
        return len(text) // 4

    def get_daily_summary(self) -> dict:
        """Returns {tokens_used, tokens_remaining, cost_usd, requests_count}"""
        today = datetime.now(timezone.utc).date().isoformat()
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute('''
                SELECT SUM(prompt_tokens + output_tokens), SUM(cost_usd), COUNT(*)
                FROM api_usage
                WHERE date(ts) = ?
            ''', (today,)).fetchone()

        tokens_used = row[0] or 0
        cost_usd = row[1] or 0.0
        requests_count = row[2] or 0
        tokens_remaining = max(0, self.config["limits"]["daily_tokens"] - tokens_used)

        return {
            "tokens_used": tokens_used,
            "tokens_remaining": tokens_remaining,
            "cost_usd": cost_usd,
            "requests_count": requests_count
        }

    def _get_monthly_cost(self) -> float:
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute('''
                SELECT SUM(cost_usd)
                FROM api_usage
                WHERE strftime('%Y-%m', ts) = ?
            ''', (month,)).fetchone()
        return row[0] or 0.0

    def start_session(self, session_id: str) -> None:
        """Register a new agent loop session for tracking."""
        ts = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute('''
                INSERT OR IGNORE INTO sessions (session_id, started_at)
                VALUES (?, ?)
            ''', (session_id, ts))

    def check_session_tokens(self, session_id: str) -> BudgetDecision:
        """Check if this session has exceeded max_tokens_per_session."""
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute('SELECT total_tokens FROM sessions WHERE session_id = ?', (session_id,)).fetchone()
        
        session_tokens = row[0] if row else 0
        limit = self.config["agent_loop"]["max_tokens_per_session"]
        if session_tokens >= limit:
            return BudgetDecision(allowed=False, reason=f"Session tokens ({session_tokens}) exceed max ({limit})", fallback="local")
        return BudgetDecision(allowed=True, reason="Within session limits", fallback="")

    def end_session(self, session_id: str) -> None:
        """Finalize session, persist totals to events.db."""
        ts = datetime.now(timezone.utc).isoformat()
        total_tokens, total_cost = 0, 0.0
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute('SELECT total_tokens, total_cost FROM sessions WHERE session_id = ?', (session_id,)).fetchone()
            if row:
                total_tokens, total_cost = row
            conn.execute('''
                UPDATE sessions
                SET ended_at = ?, status = 'completed'
                WHERE session_id = ?
            ''', (ts, session_id))
            
        # Emit to event bus
        try:
            from lib.event_bus import emit
            emit('budget_controller', 'session_ended', {
                'session_id': session_id,
                'total_tokens': total_tokens,
                'total_cost': total_cost
            })
        except ImportError:
            pass # Handle gracefully if event_bus isn't available

    def is_local_only_mode(self) -> bool:
        """True if daily limit is exhausted → caller must use local models."""
        summary = self.get_daily_summary()
        limits = self.config["limits"]
        return summary["tokens_used"] >= limits["daily_tokens"] or summary["cost_usd"] >= limits["daily_cost_usd"]

