# lib/models/adapters/anthropic.py
from __future__ import annotations
import logging
from typing import Any
import httpx
from .base import ModelAdapter

log = logging.getLogger("jarvis.models.anthropic")

class AnthropicAdapter(ModelAdapter):
    provider_name = "anthropic"

    def __init__(self, secrets_manager):
        self.sm = secrets_manager

    async def generate(self, model: str, prompt: str, stop: list[str] | None = None, max_tokens: int = 1024, **kwargs) -> tuple[str, dict[str, int]]:
        api_key = self.sm.get("anthropic_api_key")
        if not api_key:
            raise ValueError("Anthropic API key not found in secrets store.")

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload: dict[str, Any] = {
            "model": model or "claude-3-haiku-20240307",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        }
        if stop:
            payload["stop_sequences"] = stop
            
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            usage = {
                "prompt_tokens": data.get("usage", {}).get("input_tokens", 0),
                "output_tokens": data.get("usage", {}).get("output_tokens", 0)
            }
            return str(data["content"][0]["text"]), usage

    def is_available(self) -> bool:
        return self.sm.has("anthropic_api_key")
