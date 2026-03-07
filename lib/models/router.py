# lib/models/router.py
from __future__ import annotations
import logging
from .adapters.base import ModelAdapter
from ..security.context import SecurityContext

log = logging.getLogger("jarvis.models.router")

class ModelRouter:
    def __init__(self, config: dict, adapters: dict[str, ModelAdapter]):
        """
        config: dict containing routing/fallback logic
        adapters: dict of provider name -> adapter instance
        """
        self.config = config
        self.adapters = adapters

    async def generate(self, model_alias: str, prompt: str, stop: list[str] | None = None, max_tokens: int = 1024, ctx: SecurityContext = None, **kwargs) -> str:
        """
        Resolves model_alias and executes call via appropriate adapter.
        Aliasing logic:
           "reason" -> try external/claude, fallback to local/qwen
           "chat"   -> try local/llama
        Enforces security capabilities.
        """
        # Resolve alias to model spec (e.g., "external/anthropic/claude-3-opus")
        model_spec = self._resolve_alias(model_alias)
        
        provider, model_name = self._parse_spec(model_spec)
        
        # Enforce security
        if ctx:
            if provider == "ollama":
                ctx.require("model:local")
            else:
                ctx.require("model:external")

        adapter = self.adapters.get(provider)
        if not adapter:
            raise ValueError(f"No adapter found for provider: {provider}")

        # Check availability and handle fallback
        if not adapter.is_available():
            if self.config.get("fallback_on_fail", True) and provider != "ollama":
                log.warning(f"Provider {provider} unavailable, falling back to local")
                provider = "ollama"
                model_name = self.config.get("default_local", "qwen3:14b")
                adapter = self.adapters["ollama"]
                if ctx:
                    ctx.require("model:local")
            else:
                raise RuntimeError(f"Model provider {provider} is not available")

        return await adapter.generate(model_name, prompt, stop=stop, max_tokens=max_tokens, **kwargs)

    def _resolve_alias(self, alias: str) -> str:
        # Minimal resolution logic for Phase 3
        # In a real app, this would come from models.toml
        aliases = {
            "reason": "external/anthropic/claude-3-haiku-20240307",
            "chat":   "local/llama3:8b",
            "fast":   "local/mistral:7b"
        }
        return aliases.get(alias, alias)

    def _parse_spec(self, spec: str) -> tuple[str, str | None]:
        if spec.startswith("local/"):
            return "ollama", spec.split("/", 1)[1]
        if spec.startswith("external/"):
            parts = spec.split("/") # external/provider/name
            return parts[1], parts[2] if len(parts) > 2 else None
        return "ollama", spec # Default to ollama
