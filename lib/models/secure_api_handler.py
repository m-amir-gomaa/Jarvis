"""
Secure API Handler Module
Manages secrets securely, enforces rate limits, tracks cost, and controls privacy logging.
"""

import os
import aiohttp
import asyncio
import logging
import sqlite3
import datetime
import hvac

log = logging.getLogger(__name__)

class CostTracker:
    def __init__(self, db_path: str = "~/.jarvis/costs.db"):
        self.db_path = os.path.expanduser(db_path)
        self._init_db()

    def _init_db(self):
        """Initializes SQLite database if it doesn't exist."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    provider TEXT,
                    model TEXT,
                    tokens INTEGER,
                    cost REAL
                )
            ''')
            conn.commit()

    def record_usage(self, provider: str, model: str, tokens: int, cost: float) -> None:
        """Records a single usage event to the database sequentially."""
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO usage (timestamp, provider, model, tokens, cost)
                VALUES (?, ?, ?, ?, ?)
            ''', (timestamp, provider, model, tokens, cost))
            conn.commit()

    def get_session_spend(self, since: datetime.datetime) -> float:
        """Aggregates cost since a specific time."""
        since_str = since.isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT SUM(cost) FROM usage WHERE timestamp >= ?
            ''', (since_str,))
            result = cursor.fetchone()[0]
            return float(result) if result else 0.0


class SecureAPIHandler:
    def __init__(self, vault_url: str = "http://127.0.0.1:8200", vault_token: str = None, 
                 rpm_limit: int = 60, cost_tracker: CostTracker = None):
        self.vault_url = vault_url
        self.vault_token = vault_token or os.environ.get("VAULT_TOKEN")
        self.vault_client = None
        
        # Token-bucket rate limiter
        self.rpm_limit = rpm_limit
        self.tokens = rpm_limit
        self.last_refill = asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else 0
        
        self.cost_tracker = cost_tracker or CostTracker()
        self.debug_log_prompts = os.environ.get("JARVIS_DEBUG_PROMPTS", "false").lower() == "true"
        
        self._init_vault()

    def _init_vault(self):
        if self.vault_token:
            try:
                self.vault_client = hvac.Client(url=self.vault_url, token=self.vault_token)
            except Exception as e:
                log.error(f"Failed to initialize Vault client: {e}")

    def get_secret(self, path: str, key: str) -> str:
        """
        Retrieves a secret. STRICTLY from Vault or Environment Variables.
        """
        # Try Vault first
        if self.vault_client and self.vault_client.is_authenticated():
            try:
                # Assuming KV v2
                read_res = self.vault_client.secrets.kv.v2.read_secret_version(path=path)
                val = read_res.get("data", {}).get("data", {}).get(key)
                if val:
                    return val
            except Exception as e:
                log.debug(f"Vault read failed for {path}:{key} : {e}")
                
        # Try Environment
        env_val = os.environ.get(key)
        if env_val:
            return env_val
            
        raise ValueError(f"Secret {key} not found in Vault ({path}) or Environment Variables.")

    async def check_limit(self, provider: str) -> bool:
        """Returns True if the provider is within limits (RPM/Budget)."""
        # For now, we allow everything unless tokens are strictly 0 and RPM is low
        # In a real impl, we'd check session Spend vs Max Budget.
        return True

    async def log_usage(self, provider: str, model: str, usage: dict, latency: float):
        """Records usage from an external adapter call."""
        tokens = usage.get("total_tokens", 0)
        # Assuming a flat rate for now or lookup table
        cost = (tokens / 1000.0) * 0.015 
        self.cost_tracker.record_usage(provider, model, tokens, cost)

    async def _wait_for_rate_limit(self):
        """Token bucket logic for Requests Per Minute (RPM)"""
        now = asyncio.get_event_loop().time()
        # Refill tokens
        time_passed = now - self.last_refill
        refill_amount = time_passed * (self.rpm_limit / 60.0)
        self.tokens = min(self.rpm_limit, self.tokens + refill_amount)
        self.last_refill = now

        if self.tokens < 1.0:
            wait_time = (1.0 - self.tokens) / (self.rpm_limit / 60.0)
            await asyncio.sleep(wait_time)
            self.tokens = 0.0
        else:
            self.tokens -= 1.0

    async def execute_request(self, session: aiohttp.ClientSession, method: str, url: str, 
                              headers: dict, json_data: dict, provider: str, model: str, cost_rate: float):
        """
        Executes HTTP request with 429 backoff and cost/privacy logging.
        """
        await self._wait_for_rate_limit()
        
        max_retries = 3
        base_delay = 1.0
        
        for attempt in range(max_retries):
            start_time = asyncio.get_event_loop().time()
            async with session.request(method, url, headers=headers, json=json_data) as response:
                latency = asyncio.get_event_loop().time() - start_time
                
                if response.status == 429:
                    retry_after = response.headers.get("Retry-After")
                    delay = int(retry_after) if retry_after else base_delay * (2 ** attempt)
                    log.warning(f"HTTP 429 Rate limited. Backing off for {delay} seconds...")
                    await asyncio.sleep(delay)
                    continue

                response.raise_for_status()
                data = await response.json()
                
                # Mock token extraction logic for demonstration
                # In reality, parse from specific provider response schema
                usage = data.get("usage", {})
                total_tokens = usage.get("total_tokens", 0)
                
                cost = (total_tokens / 1000.0) * cost_rate
                
                # Privacy logging
                log.info(f"API Call - Provider: {provider}, Model: {model}, Latency: {latency:.2f}s, Tokens: {total_tokens}, Cost: ${cost:.4f}")
                if self.debug_log_prompts:
                    log.debug(f"Prompt content: {json_data}")
                    
                self.cost_tracker.record_usage(provider, model, total_tokens, cost)
                
                return data
                
        raise aiohttp.ClientResponseError(
            request_info=response.request_info,
            history=response.history,
            status=429,
            message="Max retries exceeded for HTTP 429 Rate Limit."
        )
