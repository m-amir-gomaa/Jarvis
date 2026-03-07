# lib/ollama_client.py
"""
Modern Ollama client bridge (Async-first with Sync wrapper).
"""
import httpx
import os
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = os.environ.get("OLLAMA_BASE_URL", base_url)

    async def chat_async(self, prompt: str, model: str | None = None, system: str | None = None) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": model or "qwen3:14b-q4_K_M",
            "prompt": prompt,
            "system": system,
            "stream": False
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=300)
                response.raise_for_status()
                return response.json().get("response", "")
        except Exception as e:
            return f"Ollama error: {e}"

    def chat(self, prompt: str, model: str | None = None, system: str | None = None) -> str:
        """Synchronous wrapper for chat_async."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            
        return loop.run_until_complete(self.chat_async(prompt, model=model, system=system))

    async def list_models_async(self) -> list[str]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/tags", timeout=5)
                response.raise_for_status()
                return [m["name"] for m in response.json().get("models", [])]
        except:
            return []

    def list_models(self) -> list[str]:
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.list_models_async())
        except RuntimeError:
            return asyncio.run(self.list_models_async())
        except:
            return []

    async def is_healthy_async(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                return (await client.get(self.base_url, timeout=2)).status_code == 200
        except:
            return False

    def is_healthy(self) -> bool:
        try:
            return asyncio.run(self.is_healthy_async())
        except:
            return False

# Module-level bridge functions for legacy code
_default_client = OllamaClient()

def chat(model: str, messages: list[dict], system: str | None = None, thinking: bool = False) -> str:
    # Convert messages list to prompt for /api/generate (bridge behavior)
    prompt = ""
    for m in messages:
        # Use simple role tags
        role = m.get('role', 'user').upper()
        content = m.get('content', '')
        prompt += f"{role}: {content}\n"
    prompt += "ASSISTANT: "
    return _default_client.chat(prompt, model=model, system=system)

def is_healthy() -> bool:
    return _default_client.is_healthy()

def list_models() -> list[str]:
    return _default_client.list_models()

async def embed(task: str, text: str) -> List[float]:
    """Modern embedding bridge."""
    url = f"{_default_client.base_url}/api/embeddings"
    payload = {"model": "nomic-embed-text", "prompt": text}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            return resp.json().get("embedding", [])
    except Exception as e:
        print(f"Embedding failed: {e}")
        return []
