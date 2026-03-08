# lib/model_router.py
"""
Model routing policy — v1/v2 bridge.
Provides Privacy enum and route() function consumed by lib/llm.py and lib/tools.py.
The actual model dispatch is handled by lib/models/router.py (v2 async hub).
This file is the synchronous policy layer that decides *whether* to use local
vs. external based on Privacy level and SecurityContext grants.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import logging
import os
import tomllib
from pathlib import Path

log = logging.getLogger("jarvis.model_router")

JARVIS_ROOT = Path(os.environ.get("JARVIS_ROOT", Path(__file__).resolve().parent.parent))


class Privacy(Enum):
    """Data sensitivity level — determines whether external APIs are eligible."""
    PRIVATE  = "private"   # Never leaves local machine
    INTERNAL = "internal"  # May use trusted external APIs (no PII)
    PUBLIC   = "public"    # No sensitivity restriction


@dataclass
class RouteDecision:
    use_local:   bool         # True → OllamaClient; False → CloudClient via OpenRouter
    model_alias: str          # e.g. "qwen3:14b-q4_K_M" or "openrouter/anthropic/claude-haiku"
    provider:    str          # "ollama" | "openrouter"
    reasoning:   str          # human-readable explanation for logs


def _load_models_config() -> dict:
    cfg_path = JARVIS_ROOT / "config" / "models.toml"
    try:
        return tomllib.loads(cfg_path.read_text()) if cfg_path.exists() else {}
    except Exception as e:
        log.warning(f"Could not load models.toml: {e}")
        return {}


def route(
    *,
    prompt: str,
    privacy: Privacy,
    ctx=None,  # SecurityContext | None
    task_type: str = "general",
) -> RouteDecision:
    """
    Apply the routing truth table to decide local vs. external.

    Truth table (abridged — full table in AUTHORITY.md §6.6):
      PRIVATE   → always local, regardless of grants
      INTERNAL  → local unless model:external granted AND provider enabled in config
      PUBLIC    → external if model:external granted AND provider enabled AND budget allows

    INVARIANT-PRIVACY-1: PRIVATE and INTERNAL data never routed to external.
    """
    from lib.prefs_manager import PrefsManager
    pm = PrefsManager()
    
    cfg = _load_models_config()
    default_local = pm.get("models.default_local", cfg.get("routing", {}).get("default_local", "qwen3:14b-q4_K_M"))
    default_ext   = pm.get("models.default_external", cfg.get("routing", {}).get("default_external", "anthropic/claude-haiku"))

    # INVARIANT-PRIVACY-1 — hard block for private data
    if privacy in (Privacy.PRIVATE, Privacy.INTERNAL):
        return RouteDecision(
            use_local=True,
            model_alias=default_local,
            provider="ollama",
            reasoning=f"Privacy={privacy.value} — local only (INVARIANT-PRIVACY-1)",
        )

    # PUBLIC — check grants and config
    if ctx is not None:
        from lib.security.exceptions import CapabilityDenied
        try:
            ctx.require("model:external")
        except (CapabilityDenied, Exception):
            return RouteDecision(
                use_local=True,
                model_alias=default_local,
                provider="ollama",
                reasoning="model:external not granted — falling back to local",
            )

    # Check config: is any external provider enabled?
    providers = cfg.get("providers", {})
    any_enabled = any(
        v.get("enabled", False)
        for k, v in providers.items()
        if k != "ollama"
    )
    if not any_enabled:
        return RouteDecision(
            use_local=True,
            model_alias=default_local,
            provider="ollama",
            reasoning="No external provider enabled in config/models.toml",
        )

    return RouteDecision(
        use_local=False,
        model_alias=default_ext,
        provider="openrouter",
        reasoning=f"Privacy=PUBLIC, model:external granted, provider enabled",
    )
