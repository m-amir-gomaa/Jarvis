# lib/llm.py
"""
v1/v2 compatibility bridge.
Provides the synchronous ask() function and Privacy enum used throughout
the existing codebase. Internally delegates to the v2 ModelRouter when
available, otherwise falls back to OllamaClient directly.

DO NOT call the Anthropic or any external API directly from this file.
All external calls must route through cloud_client.py (BudgetController gate).
"""
from __future__ import annotations
import logging
from lib.model_router import Privacy, RouteDecision, route   # noqa: F401 — re-exported

log = logging.getLogger("jarvis.llm")

# Lazy-import heavy deps so jarvis.py CLI startup is not delayed
_ollama_client = None
_model_router  = None


def _get_ollama():
    global _ollama_client
    if _ollama_client is None:
        from lib.ollama_client import OllamaClient
        _ollama_client = OllamaClient()
    return _ollama_client


def _get_router():
    global _model_router
    if _model_router is None:
        try:
            from lib.models.router import ModelRouter
            from lib.models.adapters.ollama import OllamaAdapter
            import tomllib
            from pathlib import Path
            import os
            JARVIS_ROOT = Path(os.environ.get("JARVIS_ROOT", Path(__file__).resolve().parent.parent))
            cfg_path = JARVIS_ROOT / "config" / "models.toml"
            cfg = tomllib.loads(cfg_path.read_text()) if cfg_path.exists() else {}
            adapters = {"ollama": OllamaAdapter()}
            _model_router = ModelRouter(config=cfg, adapters=adapters)
        except Exception as e:
            log.warning(f"ModelRouter unavailable ({e}), using OllamaClient fallback")
    return _model_router


from dataclasses import dataclass

@dataclass
class LLMResponse:
    content: str
    usage: dict  # {"prompt_tokens": int, "output_tokens": int}

    def __str__(self) -> str:
        return self.content

def ask(
    prompt: str,
    *,
    task: str = "general",
    model: str | None = None,
    privacy: Privacy = Privacy.PRIVATE,
    ctx=None,
    max_tokens: int = 2048,
    system: str | None = None,
    thinking: bool = False,
) -> LLMResponse:
    """
    Synchronous ask — core LLM call used by jarvis.py CLI and pipelines.
    Returns LLMResponse object.
    """
    router = _get_router()
    full_prompt = f"{system}\n\n{prompt}" if system else prompt

    if router is not None and ctx is not None:
        # v2 path: privacy-aware routing through ModelRouter
        from lib.model_router import route
        decision = route(prompt=prompt, privacy=privacy, ctx=ctx, task_type=task)
        if not decision.use_local:
            # Check budget before cloud call
            from lib.budget_controller import BudgetController
            bc = BudgetController()
            # Estimate tokens
            est = bc.estimate_tokens(full_prompt)
            budget_ok = bc.check_and_reserve(task, est)
            if not budget_ok.allowed:
                log.warning(f"Budget check failed: {budget_ok.reason}. Falling back to local.")
                decision.use_local = True

        if not decision.use_local:
            response, usage = router.call(
                model or decision.model_alias,
                full_prompt,
                ctx=ctx,
                max_tokens=max_tokens,
                thinking=thinking
            )
            return LLMResponse(content=response, usage=usage)

    # v1 fallback path: direct OllamaClient call (local only)
    ollama = _get_ollama()
    # Note: OllamaClient.chat currently returns str, we wrap it
    res = ollama.chat(full_prompt, model=model, system=system)
    # Estimate local usage (mocked as 0 cost but tracked)
    usage = {"prompt_tokens": len(full_prompt)//4, "output_tokens": len(res)//4}
    return LLMResponse(content=res, usage=usage)
