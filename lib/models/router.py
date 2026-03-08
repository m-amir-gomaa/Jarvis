# lib/models/router.py
from __future__ import annotations
import logging
from .adapters.base import ModelAdapter
from ..security.context import SecurityContext

try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass

log = logging.getLogger("jarvis.models.router")

class ModelRouter:
    def __init__(self, config: dict, adapters: dict[str, ModelAdapter]):
        """
        config: dict containing routing/fallback logic
        adapters: dict of provider name -> adapter instance
        """
        self.config = config
        self.adapters = adapters
        self._aliases = self._load_aliases()

    def _load_aliases(self) -> dict[str, str]:
        """
        Load model aliases from config/models.toml [aliases] section.
        Falls back to safe local-only qwen3 defaults if config is missing.
        Called once at init time. (FIX-MOD-1)
        """
        raw = self.config.get("aliases", {})
        if not raw:
            import logging
            logging.getLogger("jarvis.models.router").warning(
                "No [aliases] section in models.toml — using local-only defaults. "
                "Add [aliases] to config/models.toml."
            )
            return {
                "reason":   "local/qwen3:14b-q4_K_M",
                "chat":     "local/qwen3:8b",
                "fast":     "local/qwen3:1.7b",
                "coder":    "local/qwen2.5-coder:7b-instruct",
                "complete": "local/qwen3:1.7b",
                "embed":    "local/nomic-embed-text:latest",
            }
        return dict(raw)

    def get_aliases(self) -> dict[str, str]:
        """Return the current alias-to-model mapping."""
        return dict(self._aliases)

    def update_alias(self, alias: str, spec: str) -> None:
        """Dynamically update a model alias at runtime."""
        self._aliases[alias] = spec
        log.info(f"Updated alias '{alias}' to '{spec}'")

    async def generate(self, model_alias: str, prompt: str, stop: list[str] | None = None, max_tokens: int = 1024, ctx: SecurityContext = None, **kwargs) -> tuple[str, dict[str, int]]:
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

        result, usage = await adapter.generate(model_name, prompt, stop=stop, max_tokens=max_tokens, **kwargs)
        return result, usage

    def call(self, model_alias: str, prompt: str, **kwargs) -> tuple[str, dict[str, int]]:
        """Synchronous wrapper for generate()."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            # nest_asyncio is already applied at the module level.
            pass
            
        return loop.run_until_complete(self.generate(model_alias, prompt, **kwargs))

    def _resolve_alias(self, alias: str) -> str:
        return self._aliases.get(alias, alias)

    def _parse_spec(self, spec: str) -> tuple[str, str | None]:
        if spec.startswith("local/"):
            return "ollama", spec.split("/", 1)[1]
        if spec.startswith("external/"):
            parts = spec.split("/") # external/provider/name
            return parts[1], parts[2] if len(parts) > 2 else None
        return "ollama", spec # Default to ollama
