# lib/models/adapters/ollama.py
from __future__ import annotations
import json, logging
import httpx
from .base import ModelAdapter

log = logging.getLogger("jarvis.models.ollama")

class OllamaAdapter(ModelAdapter):
    provider_name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url

    async def generate(self, model: str, prompt: str, stop: list[str] | None = None, max_tokens: int = 1024, **kwargs) -> tuple[str, dict[str, int]]:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "stop": stop or []
            }
        }
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            usage = {
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "output_tokens": data.get("eval_count", 0)
            }
            return str(data.get("response", "")), usage

    def is_available(self) -> bool:
        # Simple health check
        try:
            import socket
            # Sync check for availability
            with socket.create_connection(("localhost", 11434), timeout=1):
                return True
        except:
            return False
