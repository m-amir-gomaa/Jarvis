#!/usr/bin/env python3
"""
benchmarks/system_analysis/check_api_keys.py
API key presence check — NEVER prints key values, only whether keys are set.
"""
import json
import sqlite3
from pathlib import Path

VAULT = Path("/THE_VAULT/jarvis")

PROVIDERS = [
    "anthropic",
    "openai",
    "google",
    "deepseek",
    "groq",
    "openrouter",
    "cerebras",
]


def _check_key_from_db(provider: str, db_path: Path) -> str:
    """Return 'set', 'missing', or 'db_error'."""
    if not db_path.exists():
        return "no_db"
    try:
        with sqlite3.connect(str(db_path)) as conn:
            row = conn.execute(
                "SELECT value FROM secrets WHERE key = ? AND LENGTH(value) > 0",
                (f"api_key_{provider}",)
            ).fetchone()
            return "set" if row else "missing"
    except Exception as e:
        return f"error: {e}"


def _check_key_from_env(provider: str) -> str:
    import os
    env_map = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "google": "GOOGLE_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "groq": "GROQ_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "cerebras": "CEREBRAS_API_KEY",
    }
    env_var = env_map.get(provider, "")
    val = os.environ.get(env_var, "")
    return "set_in_env" if val else "not_in_env"


def check_api_keys() -> dict:
    secrets_db = VAULT / "secrets" / "api_keys.db"
    keys = {}

    for provider in PROVIDERS:
        db_status = _check_key_from_db(provider, secrets_db)
        env_status = _check_key_from_env(provider)

        # Determine effective status
        if db_status == "set" or env_status == "set_in_env":
            effective = "available"
        elif db_status == "no_db" and env_status == "not_in_env":
            effective = "not_configured"
        else:
            effective = "missing"

        keys[provider] = {
            "vault_db": db_status,
            "environment": env_status,
            "effective": effective,
        }

    configured = [p for p, v in keys.items() if v["effective"] == "available"]
    missing = [p for p, v in keys.items() if v["effective"] == "not_configured"]

    return {
        "summary": {
            "configured": len(configured),
            "missing": len(missing),
            "providers_configured": configured,
            "providers_missing": missing,
        },
        "keys": keys,
        "note": "Key values are never printed. Only presence is checked.",
    }


if __name__ == "__main__":
    data = check_api_keys()
    print(json.dumps(data, indent=2))
