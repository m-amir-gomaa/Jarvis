#!/usr/bin/env python3
"""
Jarvis Hallucination Monitor
/home/qwerty/NixOSenv/Jarvis/pipelines/hallucination_monitor.py

Parses the system.jsonl event log for repeated /fix failures and flags them
for human review or ERS rerouting.
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict

BASE_DIR = Path(os.environ.get("JARVIS_ROOT", Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(BASE_DIR))
from lib.event_bus import emit

# Threshold: if the same error string appears this many times, flag it.
REPETITION_THRESHOLD = 3

# Expected path for the structured event log.
SYSTEM_LOG_PATH = BASE_DIR / "logs" / "system.jsonl"


def parse_log(log_path: Path) -> List[Dict[str, Any]]:
    """Parse a JSONL log file into a list of event records."""
    events = []
    if not log_path.exists():
        return events
    with open(log_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return events


def detect_hallucinations(
    log_path: Path = SYSTEM_LOG_PATH,
    threshold: int = REPETITION_THRESHOLD
) -> List[Dict[str, Any]]:
    """
    Analyze the system event log for repeated fix-command failures.

    Args:
        log_path: Path to the system.jsonl log file.
        threshold: How many repeated failures trigger a flag.

    Returns:
        A list of flagged incidents, each containing:
        - error: The repeated error string.
        - count: Number of occurrences.
        - events: All matching event records.
    """
    events = parse_log(log_path)

    # Count occurrences of each unique error string from fix-related events
    fix_failures: Dict[str, List[Dict]] = defaultdict(list)
    for event in events:
        # Event schema expected: {"action": "/fix", "status": "failure", "error": "...", ...}
        is_fix = event.get("action") == "/fix"
        is_failure = event.get("status") == "failure"
        if is_fix and is_failure:
            error_key = event.get("error", "unknown_error")
            fix_failures[error_key].append(event)

    flagged = []
    for error_str, occurrences in fix_failures.items():
        if len(occurrences) >= threshold:
            flagged.append({
                "error": error_str,
                "count": len(occurrences),
                "events": occurrences,
            })
            emit("hallucination_monitor", "flagged", {
                "error": error_str,
                "count": len(occurrences),
                "recommendation": "human_review_or_ers_reroute",
            })
            print(
                f"[HallucinationMonitor] FLAGGED: '{error_str}' repeated "
                f"{len(occurrences)} times. Recommend human review or ERS reroute."
            )

    if not flagged:
        print("[HallucinationMonitor] No hallucination patterns detected.")

    return flagged


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Jarvis Hallucination Monitor")
    parser.add_argument(
        "--log", type=Path, default=SYSTEM_LOG_PATH,
        help="Path to system.jsonl log file"
    )
    parser.add_argument(
        "--threshold", type=int, default=REPETITION_THRESHOLD,
        help="Number of repeated failures to trigger a flag"
    )
    args = parser.parse_args()

    results = detect_hallucinations(log_path=args.log, threshold=args.threshold)
    if results:
        print(f"\n[HallucinationMonitor] {len(results)} pattern(s) flagged for review.")
    else:
        print("\n[HallucinationMonitor] System looks healthy.")
