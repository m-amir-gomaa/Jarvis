# lib/models/adapters/groq.py
from .base import ModelAdapter
import httpx

class GroqAdapter(ModelAdapter):
    provider_name = "groq"
    _SECRET_KEY   = "groq_api_key"

    def __init__(self, secrets_manager):
        self.sm = secrets_manager

    async def generate(self, model_alias: str, prompt: str, **kwargs) -> tuple[str, dict[str, int]]:
        api_key = self.sm.get(self._SECRET_KEY)
        if not api_key:
            raise ValueError("Groq API key not found in secrets store.")

        model = kwargs.get("model", "llama3-70b-8192")
        url = "https://api.groq.com/openai/v1/chat/completions"
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
            usage_raw = data.get("usage", {})
            usage = {
                "prompt_tokens": usage_raw.get("prompt_tokens", 0),
                "output_tokens": usage_raw.get("completion_tokens", usage_raw.get("output_tokens", 0)),
            }
            return content, usage

    def is_available(self) -> bool:
        return self.sm.has(self._SECRET_KEY)
