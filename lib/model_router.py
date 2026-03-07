import os
import tomllib
from enum import Enum
from dataclasses import dataclass
from typing import Optional

class Privacy(Enum):
    PRIVATE  = 'private'   # personal data, local files -> LOCAL ONLY, no exceptions
    INTERNAL = 'internal'  # generic content, prefer local
    PUBLIC   = 'public'    # safe to route to cloud

@dataclass
class RouteDecision:
    backend: str        # 'local' or 'cloud'
    model_alias: str    # key in models.toml OR cloud model name
    reasoning: str      # human-readable explanation for logs

# Task routing rules (task -> default backend + alias)
TASK_RULES = {
    'complete':  ('local', 'fast'),    # ALWAYS local - latency + privacy
    'classify':  ('local', 'fast'),    # ALWAYS local - privacy sensitive
    'embed':     ('local', 'embed'),   # ALWAYS local
    'clean':     ('local', 'chat'),
    'summarize': ('local', 'chat'),
    'chat':      ('local', 'chat'),
    'fix':       ('local', 'coder'),   # local first, escalate if needed
    'diagnose':  ('local', 'coder'),
    'reason':    ('local', 'reason'),  # escalate if context > 16K
    'research':  ('local', 'chat'),    # public content - cloud allowed
}

def resolve_codebase_privacy(path: str) -> Optional[Privacy]:
    """Finds if a path falls under any configured codebase privacy tier."""
    jarvis_root = os.environ.get("JARVIS_ROOT", "/home/qwerty/NixOSenv/Jarvis")
    cb_path = os.path.join(jarvis_root, "config", "codebases.toml")
    
    if not os.path.exists(cb_path):
        return None
        
    try:
        with open(cb_path, "rb") as f:
            codebases = tomllib.load(f).get("codebases", {})
            
        # Longest match first
        best_match = None
        best_len = -1
        target = os.path.abspath(path)
        
        for cp, tier in codebases.items():
            abs_cp = os.path.abspath(cp)
            if target.startswith(abs_cp) and len(abs_cp) > best_len:
                best_len = len(abs_cp)
                best_match = tier
                
        if best_match:
            try:
                return Privacy(best_match.lower())
            except ValueError:
                pass
    except Exception:
        pass
    return None

def route(task: str,
          privacy: Privacy = Privacy.INTERNAL,
          context_tokens: int = 0,
          thinking: bool = False,
          budget_ok: bool = True,
          path: Optional[str] = None) -> RouteDecision:
    """
    Priority order:
    1. Check `config/codebases.toml` for path match -> if PRIVATE -> always local
    2. Privacy.PRIVATE -> always local
    3. thinking=True -> local:reason (Qwen3 /think mode)
    4. context > 16K + PUBLIC + budget_ok -> cloud (e.g., google/gemini-2.5-flash)
    5. budget exhausted -> force local
    6. Default task rule
    """
    # 1. Resolve path privacy if able
    if path:
        cb_priv = resolve_codebase_privacy(path)
        if cb_priv:
            # Codebases.toml takes precedence if it upgrades restriction
            if cb_priv == Privacy.PRIVATE:
                privacy = Privacy.PRIVATE
            elif cb_priv == Privacy.INTERNAL and privacy == Privacy.PUBLIC:
                privacy = Privacy.INTERNAL

    default_backend, default_alias = TASK_RULES.get(task, ('local', 'chat'))
    
    # 2. Strict Local Enforcements
    if privacy == Privacy.PRIVATE:
        # Enforce local strictly
        reasoning = "Strict local due to PRIVATE privacy tier."
        if thinking:
            return RouteDecision('local', 'reason', reasoning + " (Thinking mode)")
        return RouteDecision('local', default_alias, reasoning)

    if not budget_ok:
        reasoning = "Forced local due to budget exhaustion or missing cloud configured."
        if thinking:
            return RouteDecision('local', 'reason', reasoning + " (Thinking mode)")
        return RouteDecision('local', default_alias, reasoning)

    # 3. Thinking -> Currently only local 'reason' supports specialized deeply thought trace (qwen3)
    if thinking:
        return RouteDecision('local', 'reason', "Thinking requested, using local 'reason' model.")

    # 4. Escalate to Cloud if context is huge and privacy allows
    if context_tokens > 16000 and privacy == Privacy.PUBLIC:
        return RouteDecision('cloud', 'google/gemini-2.5-flash', "Large context > 16K on PUBLIC data, escalating to Cloud Gemini.")
    
    if context_tokens > 8000 and privacy == Privacy.PUBLIC and task == "research":
        return RouteDecision('cloud', 'anthropic/claude-3.5-sonnet', "Public research with large context, escalating to Cloud Claude.")

    # 6. Default Fallback
    return RouteDecision(default_backend, default_alias, f"Default rule applied for task '{task}'.")
