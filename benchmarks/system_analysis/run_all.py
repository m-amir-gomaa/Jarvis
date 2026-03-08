#!/usr/bin/env python3
"""
benchmarks/system_analysis/run_all.py
Orchestrates all system analysis checks and emits a unified report.

Usage:
    python benchmarks/system_analysis/run_all.py [--json] [--output PATH]
"""
import json
import sys
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

import importlib

CHECKS = [
    ("hardware",  "benchmarks.system_analysis.check_hardware",  "check_hardware"),
    ("services",  "benchmarks.system_analysis.check_services",  "check_services"),
    ("models",    "benchmarks.system_analysis.check_models",    "check_models"),
    ("knowledge", "benchmarks.system_analysis.check_knowledge", "check_knowledge"),
    ("security",  "benchmarks.system_analysis.check_security",  "check_security"),
    ("api_keys",  "benchmarks.system_analysis.check_api_keys",  "check_api_keys"),
]

STATUS_COLORS = {
    "ok":    "\033[92m✓\033[0m",
    "warn":  "\033[93m⚠\033[0m",
    "fail":  "\033[91m✗\033[0m",
    "skip":  "\033[90m–\033[0m",
}


def run_check(name: str, module_path: str, fn_name: str) -> dict:
    try:
        mod = importlib.import_module(module_path)
        fn = getattr(mod, fn_name)
        data = fn()
        return {"name": name, "status": "ok", "data": data, "error": None}
    except Exception as e:
        return {"name": name, "status": "error", "data": {}, "error": str(e)}


def _derive_status(name: str, data: dict) -> str:
    """Derive a simple health status from each check's data."""
    if name == "services":
        summary = data.get("summary", {})
        if summary.get("degraded", 0) > 0:
            return "warn"
        return "ok"
    if name == "security":
        if data.get("pending_grants", {}).get("count", 0) > 0:
            return "warn"
        if data.get("secrets_dir", {}).get("world_readable"):
            return "warn"
        return "ok"
    if name == "models":
        routing_status = data.get("routing_status", {})
        if any(v == "MISSING" for v in routing_status.values()):
            return "warn"
        return "ok" if data.get("ollama_reachable") else "fail"
    if name == "api_keys":
        configured = data.get("summary", {}).get("configured", 0)
        return "ok" if configured > 0 else "warn"
    if name == "knowledge":
        db = data.get("knowledge_db", {})
        return "ok" if db.get("exists") else "warn"
    return "ok"


def write_markdown(report: dict, out_path: Path) -> None:
    ts = report["timestamp"]
    lines = [
        "# Jarvis System Analysis Report",
        f"\n**Generated**: {ts}",
        f"**NixOS**: {report['checks'].get('hardware', {}).get('data', {}).get('is_nixos', 'unknown')}",
        "\n---\n",
    ]

    # Overall summary table
    lines.append("## Summary\n")
    lines.append("| Check | Status | Key Info |")
    lines.append("|-------|--------|----------|")

    for name, _, _ in CHECKS:
        check_result = report["checks"].get(name, {})
        status = check_result.get("health_status", "error")
        data = check_result.get("data", {})
        icon = {"ok": "✅", "warn": "⚠️", "fail": "❌", "error": "💥"}.get(status, "❓")

        if name == "hardware":
            key_info = f"{data.get('cpu_model','?')} | RAM: {data.get('ram_used_gb','?')}/{data.get('ram_total_gb','?')} GB used"
        elif name == "services":
            s = data.get("summary", {})
            key_info = f"{s.get('healthy', 0)}/{s.get('total', 0)} services healthy"
        elif name == "models":
            key_info = f"{data.get('models_available', 0)} models available, {data.get('models_loaded_in_ram', 0)} in RAM"
        elif name == "knowledge":
            kb = data.get("knowledge_db", {})
            chunks = kb.get("tables", {}).get("chunks", "?")
            key_info = f"{chunks} chunks, {data.get('inbox_pending', '?')} pending inbox items"
        elif name == "security":
            pg = data.get("pending_grants", {}).get("count", 0)
            tok = "valid" if data.get("session_token", {}).get("valid") else "expired"
            key_info = f"Session: {tok} | {pg} pending grants"
        elif name == "api_keys":
            s = data.get("summary", {})
            key_info = f"{s.get('configured', 0)}/{len(s.get('providers_configured', []) + s.get('providers_missing', []))} providers configured"
        else:
            key_info = ""

        lines.append(f"| **{name.replace('_', ' ').title()}** | {icon} {status} | {key_info} |")

    # Detailed sections
    lines.append("\n---\n")

    # Services detail
    services_data = report["checks"].get("services", {}).get("data", {})
    if services_data.get("services"):
        lines.append("## Services Detail\n")
        lines.append("| Service | Status | Uptime |")
        lines.append("|---------|--------|--------|")
        for svc, info in services_data["services"].items():
            icon = "✅" if info.get("healthy") else "❌"
            lines.append(f"| {svc} | {icon} {info.get('active_state', '?')}/{info.get('sub_state', '?')} | {info.get('uptime', 'n/a')} |")

    # Models detail
    models_data = report["checks"].get("models", {}).get("data", {})
    if models_data.get("routing_config"):
        lines.append("\n## Model Routing\n")
        lines.append("| Role | Model | Status |")
        lines.append("|------|-------|--------|")
        routing = models_data.get("routing_config", {})
        routing_status = models_data.get("routing_status", {})
        for role, model in routing.items():
            status_icon = {"ok": "✅", "MISSING": "❌", "cloud_model": "☁️", "not_configured": "–"}.get(
                routing_status.get(role, ""), "❓")
            lines.append(f"| {role} | `{model}` | {status_icon} |")

    # API keys
    keys_data = report["checks"].get("api_keys", {}).get("data", {})
    if keys_data.get("keys"):
        lines.append("\n## API Keys\n")
        lines.append("| Provider | Status |")
        lines.append("|----------|--------|")
        for provider, info in keys_data["keys"].items():
            eff = info.get("effective", "?")
            icon = "✅" if eff == "available" else "–"
            lines.append(f"| {provider} | {icon} {eff} |")

    lines.append("\n---")
    lines.append(f"\n*Report generated by `benchmarks/system_analysis/run_all.py` on {ts}*\n")

    out_path.write_text("\n".join(lines))
    print(f"[✓] Markdown report: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Jarvis System Analysis")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")
    parser.add_argument("--output", default=None, help="Output directory (default: benchmarks/results/)")
    args = parser.parse_args()

    out_dir = Path(args.output) if args.output else ROOT / "benchmarks" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().isoformat(timespec="seconds")
    report = {"timestamp": ts, "checks": {}}

    print("═" * 56)
    print("  Jarvis System Analysis Bootstrap")
    print(f"  {ts}")
    print("═" * 56)

    for name, module_path, fn_name in CHECKS:
        sys.stdout.write(f"  [{name:<12}] ")
        sys.stdout.flush()
        result = run_check(name, module_path, fn_name)
        health = _derive_status(name, result["data"]) if result["status"] == "ok" else "error"
        result["health_status"] = health
        report["checks"][name] = result

        status_icon = {"ok": "✓", "warn": "⚠", "fail": "✗", "error": "✗"}.get(health, "?")
        print(f"{status_icon}  {health}")

        if result.get("error"):
            print(f"         Error: {result['error']}")

    # Write outputs
    json_path = out_dir / "system_report.json"
    json_path.write_text(json.dumps(report, indent=2, default=str))
    print(f"\n[✓] JSON report:     {json_path}")

    md_path = out_dir / "system_report.md"
    write_markdown(report, md_path)

    if args.json:
        print(json.dumps(report, indent=2, default=str))

    # Health summary
    all_statuses = [v.get("health_status", "error") for v in report["checks"].values()]
    overall = "✅ All Clear" if all(s == "ok" for s in all_statuses) else \
              "⚠️  Warnings Present" if all(s in ("ok", "warn") for s in all_statuses) else \
              "❌ Failures Detected"
    print(f"\n  Overall: {overall}\n")


if __name__ == "__main__":
    main()
