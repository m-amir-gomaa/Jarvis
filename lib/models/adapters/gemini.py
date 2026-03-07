# lib/models/adapters/gemini.py
from .base import ModelAdapter
import httpx

class GeminiAdapter(ModelAdapter):
    provider_name = "gemini"
    _SECRET_KEY   = "gemini_api_key"

    def __init__(self, secrets_manager):
        self.sm = secrets_manager

    async def generate(self, model_alias: str, prompt: str, **kwargs) -> tuple[str, dict[str, int]]:
        api_key = self.sm.get(self._SECRET_KEY)
        if not api_key:
            raise ValueError("Gemini API key not found in secrets store.")

        model = kwargs.get("model", "gemini-1.5-pro")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=60.0)
            resp.raise_for_status()
            data = resp.json()
            
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            # Estimate usage if missing
            usage = data.get("usageMetadata", {
                "promptTokenCount": len(prompt) // 4,
                "candidatesTokenCount": len(content) // 4
            })
            return content, {
                "prompt_tokens": usage.get("promptTokenCount", 0),
                "output_tokens": usage.get("candidatesTokenCount", 0)
            }

    def is_available(self) -> bool:
        return self.sm.has(self._SECRET_KEY)
