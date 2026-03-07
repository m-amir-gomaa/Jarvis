# lib/models/adapters/openai.py
from .base import ModelAdapter
import httpx

class OpenAIAdapter(ModelAdapter):
    provider_name = "openai"
    _SECRET_KEY   = "openai_api_key"

    def __init__(self, secrets_manager):
        self.sm = secrets_manager

    async def generate(self, model: str, prompt: str, stop: list[str] | None = None, max_tokens: int = 1024, **kwargs) -> tuple[str, dict[str, int]]:
        """API call to OpenAI."""
        api_key = self.sm.get(self._SECRET_KEY)
        if not api_key:
            raise ValueError("OpenAI API key not found in secrets store.")

        # Use provided model name, fallback to gpt-4o
        model_name = model or kwargs.get("model", "gpt-4o")
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": kwargs.get("max_tokens", 1024),
            "temperature": kwargs.get("temperature", 0.7)
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload, timeout=60.0)
            resp.raise_for_status()
            data = resp.json()
            
            content = data["choices"][0]["message"]["content"]
            usage_raw = data.get("usage", {})
            usage = {
                "prompt_tokens": usage_raw.get("prompt_tokens", 0),
                "output_tokens": usage_raw.get("completion_tokens", usage_raw.get("output_tokens", 0)),
            }
            return content, usage

    def is_available(self) -> bool:
        return self.sm.has(self._SECRET_KEY)
