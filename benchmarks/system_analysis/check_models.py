#!/usr/bin/env python3
"""
benchmarks/system_analysis/check_models.py
Real Ollama model inventory and preference routing check.
"""
import json
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print(json.dumps({"error": "requests not installed"}))
    sys.exit(1)

BASE_DIR = Path(__file__).parent.parent.parent
OLLAMA_URL = "http://localhost:11434"
PREFS_PATH = Path("~/.config/jarvis/user_prefs.toml").expanduser()


def _get_ollama_models() -> list:
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if r.status_code == 200:
            return r.json().get("models", [])
    except Exception:
        pass
    return []


def _get_ollama_running() -> list:
    """Models currently loaded in memory."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/ps", timeout=5)
        if r.status_code == 200:
            return r.json().get("models", [])
    except Exception:
        pass
    return []


def _load_prefs() -> dict:
    if not PREFS_PATH.exists():
        return {}
    try:
        import tomllib
        with open(PREFS_PATH, "rb") as f:
            return tomllib.load(f).get("models", {})
    except Exception:
        return {}


def check_models() -> dict:
    ollama_reachable = False
    available = []
    running = []

    try:
        raw_models = _get_ollama_models()
        ollama_reachable = True
        for m in raw_models:
            size_gb = round(m.get("size", 0) / 1024**3, 2)
            available.append({
                "name": m.get("name", ""),
                "size_gb": size_gb,
                "modified_at": m.get("modified_at", ""),
            })
        raw_running = _get_ollama_running()
        for m in raw_running:
            size_vram = round(m.get("size_vram", 0) / 1024**3, 2)
            running.append({
                "name": m.get("name", ""),
                "vram_gb": size_vram,
                "until": m.get("expires_at", ""),
            })
    except Exception as e:
        pass

    prefs = _load_prefs()
    routing = {
        "default_local": prefs.get("default_local", "not_configured"),
        "default_cloud": prefs.get("default_cloud", "not_configured"),
        "coding_model": prefs.get("coding_model", "not_configured"),
        "fast_model": prefs.get("fast_model", "not_configured"),
        "research_model": prefs.get("research_model", "not_configured"),
        "thinking_model": prefs.get("thinking_model", "not_configured"),
    }

    # Validate routing: check if configured models are actually available
    available_names = {m["name"] for m in available}
    routing_status = {}
    for role, model_name in routing.items():
        if model_name == "not_configured":
            routing_status[role] = "not_configured"
        elif model_name in available_names:
            routing_status[role] = "ok"
        elif ":" not in model_name:
            routing_status[role] = "cloud_model"
        else:
            routing_status[role] = "MISSING"  # configured but not pulled

    return {
        "ollama_reachable": ollama_reachable,
        "models_available": len(available),
        "models_loaded_in_ram": len(running),
        "available": available,
        "currently_running": running,
        "routing_config": routing,
        "routing_status": routing_status,
    }


if __name__ == "__main__":
    data = check_models()
    print(json.dumps(data, indent=2))
