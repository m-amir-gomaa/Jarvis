#!/usr/bin/env python3
"""
MVP 10 — NixOS Validator
/home/qwerty/NixOSenv/Jarvis/lib/nix_validator.py  (also: pipelines/nixos_validator.py)

Runs `nix flake check` on the NixOS config repo, captures any errors,
passes them to Qwen3-14B for diagnosis, and saves a report to review/.
"""

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/home/qwerty/NixOSenv/Jarvis")
from lib.event_bus import emit
from lib.model_router import route
from lib.ollama_client import chat, is_healthy

REVIEW_DIR = Path("/home/qwerty/NixOSenv/Jarvis/review")
NIX_REPO = Path("/home/qwerty/NixOSenv")
EXPERT_PROMPT_PATH = Path("/home/qwerty/NixOSenv/Jarvis/prompts/nixos/best.txt")

DEFAULT_EXPERT = (
    "You are an expert NixOS engineer specializing in flake-based configurations. "
    "The system is an Intel i7-1165G7 laptop with Intel Iris Xe graphics (NO NVIDIA). "
    "Ollama is running as ollama-cpu (CPU-only). Never suggest cudaPackages. "
    "Diagnose the following error and provide a minimal, idiomatic fix."
)


def load_expert_prompt() -> str:
    if EXPERT_PROMPT_PATH.exists():
        return EXPERT_PROMPT_PATH.read_text().strip()
    return DEFAULT_EXPERT


def run_flake_check(repo: Path) -> tuple[bool, str]:
    """Run nix flake check. Returns (success, output)."""
    try:
        result = subprocess.run(
            ["nix", "flake", "check", "--no-build"],
            cwd=str(repo),
            capture_output=True, text=True,
            timeout=120,  # nix flake check can hang
        )
        output = result.stdout + result.stderr
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "ERROR: nix flake check timed out after 120s"
    except Exception as e:
        return False, f"ERROR: {e}"


def run_nixos_rebuild_dry(repo: Path) -> tuple[bool, str]:
    """Run nixos-rebuild dry-build to catch evaluation errors."""
    try:
        result = subprocess.run(
            ["nixos-rebuild", "dry-build", "--flake", f"{repo}#nixos"],
            capture_output=True, text=True,
            timeout=120,
        )
        output = result.stdout + result.stderr
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "ERROR: nixos-rebuild dry-build timed out after 120s"
    except Exception as e:
        return False, f"ERROR: {e}"


def diagnose_error(error_output: str) -> str:
    """Use Qwen3-14B with thinking to diagnose the NixOS error."""
    if not is_healthy():
        return "(Ollama offline — cannot diagnose)"
    system = load_expert_prompt()
    messages = [{"role": "user", "content": f"NixOS error:\n\n{error_output[:3000]}"}]
    try:
        decision = route("diagnose")
        return chat(decision.model_alias, messages, system=system, thinking=True)
    except Exception as e:
        return f"(diagnosis failed: {e})"


def save_report(success: bool, check_output: str, diagnosis: str) -> Path:
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    status = "ok" if success else "error"
    path = REVIEW_DIR / f"nixos_validation_{ts}_{status}.md"
    with open(path, "w") as f:
        f.write(f"# NixOS Validation Report — {ts}\n\n")
        f.write(f"**Status**: {'✅ PASSED' if success else '❌ FAILED'}\n\n")
        f.write(f"## Command Output\n\n```\n{check_output[:3000]}\n```\n\n")
        if not success:
            f.write(f"## AI Diagnosis\n\n{diagnosis}\n")
    return path


def main():
    parser = argparse.ArgumentParser(description="Jarvis NixOS Validator (MVP 10)")
    parser.add_argument("--repo", default=str(NIX_REPO), help="Path to NixOS flake repo")
    parser.add_argument("--dry", action="store_true", help="Use nixos-rebuild dry-build instead of flake check")
    args = parser.parse_args()

    repo = Path(args.repo)
    print(f"[NixOS Validator] Checking: {repo}")

    if args.dry:
        success, output = run_nixos_rebuild_dry(repo)
        cmd = "nixos-rebuild dry-build"
    else:
        success, output = run_flake_check(repo)
        cmd = "nix flake check"

    if success:
        print(f"[NixOS Validator] ✅ {cmd} passed.")
        path = save_report(True, output, "")
        emit("nix_validator", "passed", {"repo": str(repo)})
    else:
        print(f"[NixOS Validator] ❌ Errors detected. Diagnosing...")
        diagnosis = diagnose_error(output)
        path = save_report(False, output, diagnosis)
        print(f"\n--- Diagnosis ---\n{diagnosis[:600]}...")
        emit("nix_validator", "failed", {"repo": str(repo), "report": str(path)})

    print(f"[NixOS Validator] Report: {path}")
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
