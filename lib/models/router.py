# lib/models/router.py
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional, Tuple
from .adapters.base import ModelAdapter
from ..security.context import SecurityContext
from .hybrid_router import HybridRouter
from .prompt_refiner import PromptRefiner
from .secure_api_handler import SecureAPIHandler

try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass

log = logging.getLogger("jarvis.models.router")

class ModelRouter:
    """
    Unified Model Router that integrates the new HybridRouter logic,
    PromptRefiner, and SecureAPIHandler.
    """
    def __init__(self, config: dict, adapters: dict[str, ModelAdapter]):
        self.config = config
        self.adapters = adapters
        
        # New Agentic Intel components
        self.secure_handler = SecureAPIHandler() # Uses Vault/Env
        self.refiner = PromptRefiner() # Uses ~/.jarvis/prompts/
        
        # Extract capability profiles for HybridRouter
        capabilities = self._extract_capabilities()
        self.hybrid_logic = HybridRouter(config=config, capabilities=capabilities)
        
        self._aliases = self._load_aliases()

    def _extract_capabilities(self) -> dict:
        """Map adapters and config to a capability profile for HybridRouter."""
        caps = {}
        # Default local capabilities
        caps["qwen3:14b-q4_K_M"] = {"capability_score": 0.8, "is_local": True}
        caps["qwen3:8b"] = {"capability_score": 0.6, "is_local": True}
        caps["qwen3:1.7b"] = {"capability_score": 0.3, "is_local": True}
        caps["qwen2.5-coder:7b-instruct"] = {"capability_score": 0.75, "is_local": True}
        
        # Cloud (typical scores)
        caps["claude-3-5-sonnet-latest"] = {"capability_score": 0.95, "is_local": False, "cost_per_1k": 0.015}
        caps["gpt-4o"] = {"capability_score": 0.95, "is_local": False, "cost_per_1k": 0.015}
        
        # Update from config if present
        caps.update(self.config.get("capabilities", {}))
        return caps

    def _load_aliases(self) -> dict[str, str]:
        raw = self.config.get("aliases", {})
        if not raw:
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
        return dict(self._aliases)

    def update_alias(self, alias: str, spec: str) -> None:
        self._aliases[alias] = spec
        log.info(f"Updated alias '{alias}' to '{spec}'")

    async def generate(self, model_alias: str, prompt: str, stop: list[str] | None = None, max_tokens: int = 1024, ctx: SecurityContext = None, **kwargs) -> tuple[str, dict[str, int]]:
        """
        Integrated generation with refinement and hybrid routing.
        """
        # 1. Hybrid Route (using raw prompt for complexity scoring)
        if model_alias in self._aliases:
            if model_alias in ["reason", "chat", "coder"]:
                target_model = self.hybrid_logic.route(prompt)
            else:
                target_model = self._resolve_alias(model_alias)
        else:
            target_model = model_alias
            
        provider, model_name = self._parse_spec(target_model)
        
        # 2. Refine Prompt (Context Injection + Provider Formatting)
        task_type = "coding" if "coder" in model_alias or "complete" in model_alias else "general"
        refined_prompt = self.refiner.format_prompt(
            task_type=task_type,
            context={"query": prompt},
            model_provider=provider
        )
        
        # 3. Security & Rate Limiting (SecureAPIHandler)
        if provider != "ollama":
            if not await self.secure_handler.check_limit(provider):
                 log.warning(f"Rate limit hit for {provider}, falling back to local")
                 provider = "ollama"
                 model_name = "qwen3:14b-q4_K_M"
                 # Re-apply formatting for local
                 refined_prompt = self.refiner.format_prompt(
                     task_type=task_type,
                     context={"query": prompt},
                     model_provider=provider
                 )
        
        if ctx:
            if provider == "ollama":
                ctx.require("model:local")
            else:
                ctx.require("model:external")

        adapter = self.adapters.get(provider)
        if not adapter:
             raise ValueError(f"No adapter found for provider: {provider}")

        # 4. Check Availability & Handle Fallback
        if not adapter.is_available():
            if self.config.get("fallback_on_fail", True) and provider != "ollama":
                log.warning(f"Provider {provider} unavailable, falling back to local")
                provider = "ollama"
                model_name = self.config.get("default_local", "qwen3:14b-q4_K_M")
                adapter = self.adapters["ollama"]
                if ctx: ctx.require("model:local")
            else:
                raise RuntimeError(f"Model provider {provider} is not available")

        # 5. Execute with Cost Tracking
        start_time = time.time()
        result, usage = await adapter.generate(model_name, refined_prompt, stop=stop, max_tokens=max_tokens, **kwargs)
        latency = time.time() - start_time
        
        if provider != "ollama":
            await self.secure_handler.log_usage(provider, model_name, usage, latency)

        return result, usage

    def call(self, model_alias: str, prompt: str, **kwargs) -> tuple[str, dict[str, int]]:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.generate(model_alias, prompt, **kwargs))

    def _resolve_alias(self, alias: str) -> str:
        return self._aliases.get(alias, alias)

    def _parse_spec(self, spec: str) -> tuple[str, str | None]:
        if spec.startswith("local/"):
            return "ollama", spec.split("/", 1)[1]
        if spec.startswith("external/"):
            parts = spec.split("/")
            return parts[1], parts[2] if len(parts) > 2 else None
        return "ollama", spec

import time # For time.time() in generate
