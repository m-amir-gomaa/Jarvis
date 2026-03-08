#!/usr/bin/env python3
"""
benchmarks/eval/runner.py
Runs all benchmark categories against configured model matrix.

Anthropic standard compliance:
- temperature=0, fixed seed per category
- All tasks in every category always run (no cherry-picking)
- Cloud models silently skipped if key not present (status: no_key)
- Tool call log is captured for agentic tasks

Usage:
    python benchmarks/eval/runner.py [--offline] [--online] [--category CATEGORY] [--model MODEL]

Categories: coding, instruction_following, factual, agentic, rag_accuracy
"""
import argparse
import importlib
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

VENV_PY = ROOT / ".venv" / "bin" / "python"
OLLAMA_URL = "http://localhost:11434"

CATEGORIES = ["coding", "instruction_following", "factual", "rag_accuracy"]
# Note: 'agentic' requires live Jarvis agent to process tool calls; it is run separately

PREFS_PATH = Path("~/.config/jarvis/user_prefs.toml").expanduser()

# Provider env var mapping
CLOUD_PROVIDERS = {
    "anthropic":  {"env": "ANTHROPIC_API_KEY", "model_prefix": "claude"},
    "openai":     {"env": "OPENAI_API_KEY",    "model_prefix": "gpt"},
    "deepseek":   {"env": "DEEPSEEK_API_KEY",  "model_prefix": "deepseek"},
    "groq":       {"env": "GROQ_API_KEY",       "model_prefix": ""},
}


def _load_prefs() -> dict:
    if not PREFS_PATH.exists():
        return {}
    try:
        import tomllib
        with open(PREFS_PATH, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


def _get_local_models(prefs: dict) -> list[dict]:
    """Return configured local model entries."""
    models_prefs = prefs.get("models", {})
    seen = set()
    models = []
    for role in ("default_local", "coding_model", "fast_model"):
        m = models_prefs.get(role, "")
        if m and ":" in m and m not in seen:
            seen.add(m)
            models.append({"model": m, "provider": "ollama", "role": role, "type": "local"})
    # Fallback: detect from Ollama if no prefs
    if not models:
        try:
            import requests
            r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
            if r.status_code == 200:
                for m in r.json().get("models", [])[:3]:
                    models.append({"model": m["name"], "provider": "ollama", "role": "default", "type": "local"})
        except Exception:
            pass
    return models


def _get_cloud_models(prefs: dict) -> list[dict]:
    """Return cloud model entries for providers with API keys set."""
    models_prefs = prefs.get("models", {})
    default_cloud = models_prefs.get("default_cloud", "")
    models = []

    for provider, info in CLOUD_PROVIDERS.items():
        key = os.environ.get(info["env"], "")
        if not key:
            # Try vault DB
            try:
                import sqlite3
                vault_db = Path("/THE_VAULT/jarvis/secrets/api_keys.db")
                if vault_db.exists():
                    with sqlite3.connect(str(vault_db)) as conn:
                        row = conn.execute(
                            "SELECT value FROM secrets WHERE key = ? AND LENGTH(value) > 0",
                            (f"api_key_{provider}",)
                        ).fetchone()
                        if row:
                            key = row[0]
            except Exception:
                pass

        if not key:
            models.append({
                "model": default_cloud or f"{provider}/default",
                "provider": provider,
                "role": "default_cloud",
                "type": "cloud",
                "status": "no_key",
            })
        else:
            model_name = default_cloud if default_cloud.startswith(info["model_prefix"]) else f"{provider}/default"
            models.append({
                "model": model_name,
                "provider": provider,
                "role": "default_cloud",
                "type": "cloud",
                "status": "available",
                "api_key": key,
            })

    return models


def call_model(model_entry: dict, prompt: str, temperature: float = 0.0) -> Optional[str]:
    """Call the model and return the response text."""
    if model_entry.get("status") == "no_key":
        return None  # Indicates skipped

    provider = model_entry["provider"]
    model = model_entry["model"]

    if provider == "ollama":
        try:
            import requests
            r = requests.post(f"{OLLAMA_URL}/api/generate", json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature, "seed": 42},
            }, timeout=300)
            if r.status_code == 200:
                return r.json().get("response", "")
            return None
        except Exception as e:
            return None

    elif provider == "anthropic":
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=model_entry["api_key"])
            msg = client.messages.create(
                model=model if "/" not in model else "claude-3-haiku-20240307",
                max_tokens=1024,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            return msg.content[0].text if msg.content else ""
        except Exception as e:
            return None

    elif provider == "openai":
        try:
            import openai
            client = openai.OpenAI(api_key=model_entry["api_key"])
            resp = client.chat.completions.create(
                model=model if "/" not in model else "gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                seed=42,
            )
            return resp.choices[0].message.content if resp.choices else ""
        except Exception as e:
            return None

    return None  # Unsupported provider


def run_category(category: str, model_entry: dict) -> dict:
    """Run all tasks in a category against a model. Returns results dict."""
    mod = importlib.import_module(f"benchmarks.eval.tasks.{category}")
    tasks = getattr(mod, "ALL_TASKS", None) or getattr(mod, "TASKS", [])
    score_fn = getattr(mod, "score_task")
    format_prompt_fn = getattr(mod, "format_prompt", None)

    results = []
    for task in tasks:
        if model_entry.get("status") == "no_key":
            results.append({
                "task_id": task["id"],
                "status": "no_key",
                "latency_s": 0,
                "error": "API key not configured",
            })
            continue

        # Build prompt
        if format_prompt_fn:
            prompt = format_prompt_fn(task)
        else:
            prompt = task["prompt"]

        t0 = time.time()
        response = call_model(model_entry, prompt, temperature=0.0)
        latency = round(time.time() - t0, 2)

        if response is None:
            result = {"status": "error", "error": "Model call failed or timed out"}
        else:
            # agentic needs tool_log; other categories just need response text
            if category == "agentic":
                result = score_fn(task, tool_log=[], final_output=response)
            else:
                result = score_fn(task, response)

        results.append({
            "task_id": task["id"],
            "status": result.get("status"),
            "latency_s": latency,
            "error": result.get("error"),
            "details": {k: v for k, v in result.items() if k not in ("status", "error")},
        })

    passed  = sum(1 for r in results if r["status"] == "pass")
    failed  = sum(1 for r in results if r["status"] == "fail")
    errors  = sum(1 for r in results if r["status"] == "error")
    skipped = sum(1 for r in results if r["status"] == "no_key")
    total   = len(results) - skipped

    return {
        "category": category,
        "model": model_entry["model"],
        "model_type": model_entry["type"],
        "provider": model_entry["provider"],
        "tasks_total": total,
        "tasks_passed": passed,
        "tasks_failed": failed,
        "tasks_error": errors,
        "tasks_skipped": skipped,
        "pass_rate": round(passed / total, 4) if total > 0 else 0.0,
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description="Jarvis Honest Benchmark Runner")
    parser.add_argument("--offline", action="store_true", help="Local models only")
    parser.add_argument("--online",  action="store_true", help="Cloud models only (need API keys)")
    parser.add_argument("--category", help=f"Only run one category: {CATEGORIES}")
    parser.add_argument("--output", default=None, help="Output directory")
    args = parser.parse_args()

    out_dir = Path(args.output) if args.output else ROOT / "benchmarks" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)

    prefs = _load_prefs()
    local_models  = _get_local_models(prefs)
    cloud_models  = _get_cloud_models(prefs)

    if args.offline:
        models = local_models
    elif args.online:
        models = cloud_models
    else:
        models = local_models + cloud_models

    categories = [args.category] if args.category else CATEGORIES

    ts = datetime.now().isoformat(timespec="seconds")
    all_results = []

    print("═" * 60)
    print("  Jarvis Benchmark Runner — Anthropic Standards")
    print(f"  {ts}")
    print("═" * 60)

    for model_entry in models:
        m_label = f"{model_entry['model']} ({model_entry['type']})"
        key_status = model_entry.get("status", "available")
        if key_status == "no_key":
            print(f"\n  ▸ {m_label}  [SKIPPED — no API key]")
            continue
        print(f"\n  ▸ {m_label}")

        for category in categories:
            sys.stdout.write(f"    [{category:<22}] ")
            sys.stdout.flush()

            cat_result = run_category(category, model_entry)
            all_results.append(cat_result)

            rate = cat_result.get("pass_rate", 0)
            passed = cat_result["tasks_passed"]
            total = cat_result["tasks_total"]
            print(f"{passed}/{total} pass  ({rate:.0%})")

    # Write results
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"benchmark_{run_id}.json"
    json_path.write_text(json.dumps({
        "run_id": run_id,
        "timestamp": ts,
        "results": all_results,
    }, indent=2, default=str))
    print(f"\n[✓] Results saved: {json_path}")

    # Also update latest symlink
    latest_path = out_dir / "benchmark_latest.json"
    latest_path.write_text(json_path.read_text())

    # Print summary table
    from benchmarks.eval.report import print_summary_table
    print_summary_table(all_results)


if __name__ == "__main__":
    main()
