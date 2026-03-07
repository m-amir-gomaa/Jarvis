# lib/models/adapters/mistral.py
from .base import ModelAdapter
import httpx

class MistralAdapter(ModelAdapter):
    provider_name = "mistral"
    _SECRET_KEY   = "mistral_api_key"

    def __init__(self, secrets_manager):
        self.sm = secrets_manager

    async def generate(self, model_alias: str, prompt: str, **kwargs) -> tuple[str, dict[str, int]]:
        api_key = self.sm.get(self._SECRET_KEY)
        if not api_key:
            raise ValueError("Mistral API key not found in secrets store.")

        model = kwargs.get("model", "mistral-large-latest")
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}]
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload, timeout=60.0)
            resp.raise_for_status()
            data = resp.json()
            
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {"prompt_tokens": 0, "output_tokens": 0})
            return content, usage

    def is_available(self) -> bool:
        return self.sm.has(self._SECRET_KEY)
