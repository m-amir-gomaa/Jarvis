#!/usr/bin/env python3
"""
MVP 6 — Prompt Optimizer
/home/qwerty/NixOSenv/Jarvis/pipelines/optimizer.py

Self-improving engine: generates prompt variants via meta-prompt,
evaluates each variant against test inputs using quality rules,
and promotes the winner to best.txt (with regression protection).

CLI:
    python optimizer.py <task_name> [--rounds N] [--max-time SECONDS] [--dry-run]

Reads: /THE_VAULT/prompts/<task>/spec.json
Writes:
  - /THE_VAULT/prompts/<task>/best.txt   (winner, if better than current)
  - /THE_VAULT/prompts/<task>/runs/<ISO>.json  (full history)
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

# Runtime paths
PROMPTS_DIR = Path("/home/qwerty/NixOSenv/Jarvis/prompts")

sys.path.insert(0, "/home/qwerty/NixOSenv/Jarvis")
from lib.ollama_client import chat, OllamaError
from lib.model_router import route
from lib.event_bus import emit


# ── Spec Loading ──────────────────────────────────────────────────────────────

def load_spec(task_name: str) -> dict:
    spec_path = PROMPTS_DIR / task_name / "spec.json"
    if not spec_path.exists():
        print(f"ERROR: spec.json not found at {spec_path}", file=sys.stderr)
        sys.exit(1)
    with open(spec_path, "r") as f:
        try:
            spec = json.load(f)
        except json.JSONDecodeError as e:
            print(f"ERROR: spec.json is malformed: {e}", file=sys.stderr)
            sys.exit(1)

    required = ["task_name", "task_description", "test_inputs", "quality_rules"]
    for key in required:
        if key not in spec:
            print(f"ERROR: spec.json missing required key: '{key}'", file=sys.stderr)
            sys.exit(1)

    return spec


# ── Variant Generation ────────────────────────────────────────────────────────

def generate_variants(spec: dict, num_variants: int) -> list[str]:
    """Use Qwen3-14B with thinking to generate N distinct prompt variants."""
    meta_prompt = f"""You are a prompt engineering expert. Your job is to generate {num_variants} DISTINCT prompts for the following task.

Task: {spec['task_description']}

Each prompt will be used as a system message for an LLM. The prompts should:
- Be clear, specific, and actionable
- Have different approaches (e.g., strict rules, examples-based, step-by-step, etc.)
- Be optimized for the quality rules: {[r['type'] for r in spec['quality_rules']]}

Output ONLY a valid JSON array of {num_variants} strings. No preamble, no commentary.
Example format: ["prompt one text", "prompt two text", ...]"""

    messages = [{"role": "user", "content": meta_prompt}]

    print(f"  Generating {num_variants} variants via meta-prompt (thinking mode)...")
    response = chat(
        model_alias=route("reason").model_alias,
        messages=messages,
        thinking=True,
        temperature=0.7,
    )

    # Extract JSON array from response
    match = re.search(r'\[.*\]', response, re.DOTALL)
    if not match:
        print(f"  WARNING: Could not parse JSON array from meta-prompt response. Raw: {response[:200]}")
        return []

    try:
        variants = json.loads(match.group(0))
        if not isinstance(variants, list):
            return []
        return [str(v) for v in variants[:num_variants]]
    except json.JSONDecodeError as e:
        print(f"  WARNING: JSON parse error from meta-prompt: {e}")
        return []


# ── Quality Scoring ───────────────────────────────────────────────────────────

def _score_not_contains(output: str, value: str, weight: float) -> float:
    """Returns weight if output does NOT contain value, else 0."""
    return weight if value not in output else 0.0

def _score_contains_all(output: str, values: list[str], weight: float) -> float:
    """Returns weight if all values are present in output, else 0."""
    return weight if all(v in output for v in values) else 0.0

def _score_length_ratio(output: str, original: str, min_r: float, max_r: float, weight: float) -> float:
    """Returns weight if len(output)/len(original) is within [min_r, max_r]."""
    if not original:
        return 0.0
    ratio = len(output) / len(original)
    return weight if min_r <= ratio <= max_r else 0.0

def _score_llm_judge(output: str, criteria: str, weight: float) -> float:
    """Use Mistral-7B to score output quality. Returns 0.0 to weight."""
    judge_prompt = f"""Rate this text on a scale of 0.0 to 1.0 for: {criteria}

Text to rate:
{output[:1500]}

Output ONLY a single float number between 0.0 and 1.0. Nothing else."""
    try:
        response = chat(
            model_alias=route("score").model_alias,
            messages=[{"role": "user", "content": judge_prompt}],
            thinking=False,
            temperature=0.1,
        )
        score = float(re.search(r'[01]?\.\d+', response.strip()).group(0))
        return round(min(max(score, 0.0), 1.0) * weight, 4)
    except Exception:
        return 0.0

def score_output(output: str, original_input: str, quality_rules: list[dict]) -> float:
    """Compute total weighted score for a given output against quality rules."""
    total = 0.0
    for rule in quality_rules:
        rule_type = rule.get("type")
        weight = rule.get("weight", 1.0)

        if rule_type == "not_contains":
            total += _score_not_contains(output, rule["value"], weight)
        elif rule_type == "contains_all":
            total += _score_contains_all(output, rule["values"], weight)
        elif rule_type == "length_ratio":
            total += _score_length_ratio(output, original_input, rule["min"], rule["max"], weight)
        elif rule_type == "llm_judge":
            total += _score_llm_judge(output, rule.get("criteria", "quality"), weight)

    return round(total, 4)


# ── Evaluation ────────────────────────────────────────────────────────────────

def evaluate_variant(variant_prompt: str, test_inputs: list[str], quality_rules: list[dict]) -> float:
    """Run variant against all test inputs and average the scores."""
    scores = []
    for test_file in test_inputs:
        if not os.path.exists(test_file):
            print(f"    WARNING: test input not found: {test_file}, skipping.")
            continue
        with open(test_file, "r") as f:
            original = f.read()

        try:
            output = chat(
                model_alias=route("score").model_alias,
                messages=[{"role": "user", "content": original[:3000]}],
                system=variant_prompt,
                thinking=False,
                temperature=0.2,
            )
            score = score_output(output, original, quality_rules)
            scores.append(score)
        except OllamaError as e:
            print(f"    ERROR during evaluation: {e}")
            scores.append(0.0)

    return round(sum(scores) / len(scores), 4) if scores else 0.0


# ── Persistence ───────────────────────────────────────────────────────────────

def load_current_best_score(task_name: str, quality_rules: list[dict], test_inputs: list[str]) -> float:
    """Score the existing best.txt to establish baseline for regression protection."""
    best_path = PROMPTS_DIR / task_name / "best.txt"
    if not best_path.exists():
        return 0.0  # No baseline, anything is an improvement
    with open(best_path, "r") as f:
        best_prompt = f.read().strip()
    return evaluate_variant(best_prompt, test_inputs, quality_rules)

def save_run(task_name: str, results: list[dict], winner_idx: int | None) -> Path:
    """Save the full run log to runs/<ISO>.json."""
    runs_dir = PROMPTS_DIR / task_name / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    iso = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_path = runs_dir / f"{iso}.json"
    with open(run_path, "w") as f:
        json.dump({
            "timestamp": iso,
            "winner_index": winner_idx,
            "results": results,
        }, f, indent=2)
    return run_path

def promote_best(task_name: str, variant: str) -> None:
    """Write the winning variant to best.txt."""
    best_path = PROMPTS_DIR / task_name / "best.txt"
    best_path.parent.mkdir(parents=True, exist_ok=True)
    with open(best_path, "w") as f:
        f.write(variant + "\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def print_results_table(results: list[dict], promoted_idx: int | None) -> None:
    print(f"\n{'Variant':<10} {'Score':<10} {'Promoted':<10}")
    print("-" * 30)
    for r in results:
        promoted = "✓ YES" if r["index"] == promoted_idx else "-"
        print(f"  {r['index']:<8} {r['score']:<10.4f} {promoted}")


def main():
    parser = argparse.ArgumentParser(description="Jarvis Prompt Optimizer (MVP 6)")
    parser.add_argument("task_name", help="Name of the prompt task (matches /THE_VAULT/prompts/<task>/)")
    parser.add_argument("--rounds", type=int, default=1, help="Number of optimization rounds (default: 1)")
    parser.add_argument("--max-time", type=int, default=3600, help="Max wall-clock seconds (default: 3600)")
    parser.add_argument("--dry-run", action="store_true", help="Generate variants only, skip scoring and promotion")
    args = parser.parse_args()

    # Load and validate spec
    spec = load_spec(args.task_name)
    num_variants = spec.get("num_variants", 5)
    quality_rules = spec["quality_rules"]
    test_inputs = spec["test_inputs"]

    print(f"[Optimizer] Task: {spec['task_name']}")
    print(f"[Optimizer] Description: {spec['task_description']}")
    print(f"[Optimizer] Variants: {num_variants} | Rounds: {args.rounds}")

    start_time = time.time()
    run_promoted_idx = None

    for round_num in range(1, args.rounds + 1):
        elapsed = time.time() - start_time
        if elapsed > args.max_time:
            print(f"\n[Optimizer] Max time ({args.max_time}s) reached at round {round_num}. Stopping.")
            emit("optimizer", "timeout", {"task": args.task_name, "round": round_num})
            break

        print(f"\n── Round {round_num}/{args.rounds} ──────────────────────────")
        variants = generate_variants(spec, num_variants)

        if not variants:
            print("  ERROR: No variants generated. Skipping round.")
            continue

        if args.dry_run:
            print("\n[Dry-run] Generated variants:")
            for i, v in enumerate(variants, 1):
                print(f"  [{i}] {v[:120]}...")
            continue

        # Baseline from existing best.txt (for regression protection)
        print(f"\n  Evaluating baseline (current best.txt)...")
        baseline_score = load_current_best_score(args.task_name, quality_rules, test_inputs)
        print(f"  Baseline score: {baseline_score:.4f}")

        # Evaluate each variant
        results = []
        for i, variant in enumerate(variants, 1):
            print(f"  Evaluating variant {i}/{len(variants)}...")
            score = evaluate_variant(variant, test_inputs, quality_rules)
            results.append({"index": i, "score": score, "prompt": variant})
            print(f"    → Score: {score:.4f}")

        # Find winner (highest score)
        best_result = max(results, key=lambda r: r["score"])

        # Regression protection: only promote if better than baseline
        promoted_idx = None
        if best_result["score"] > baseline_score:
            promote_best(args.task_name, best_result["prompt"])
            promoted_idx = best_result["index"]
            run_promoted_idx = promoted_idx
            print(f"\n  ✓ New winner promoted (score {best_result['score']:.4f} > baseline {baseline_score:.4f})")
            emit("optimizer", "promoted", {"task": args.task_name, "score": best_result["score"]})
        else:
            print(f"\n  ✗ No improvement. Best: {best_result['score']:.4f}, Baseline: {baseline_score:.4f}. best.txt unchanged.")
            emit("optimizer", "no_improvement", {"task": args.task_name, "best_score": best_result["score"]})

        # Save run log
        run_path = save_run(args.task_name, results, promoted_idx)
        print(f"  Run log: {run_path}")

        print_results_table(results, promoted_idx)

    print("\n[Optimizer] Done.")


if __name__ == "__main__":
    main()
