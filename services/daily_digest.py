#!/usr/bin/env python3
"""
MVP 13 (complete) — Daily Digest
/THE_VAULT/jarvis/services/daily_digest.py

Queries events.db for yesterday's activity, summarizes via Mistral-7B,
appends to daily_digest.md, and sends a desktop notification.

Triggered by: systemd timer jarvis-daily-digest (06:00 daily)
"""

import os
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/THE_VAULT/jarvis")
from lib.event_bus import emit, query_events
from lib.ollama_client import chat, is_healthy
from lib.model_router import route

DIGEST_PATH = Path("/THE_VAULT/jarvis/logs/daily_digest.md")


def get_yesterday_events() -> list[dict]:
    import sqlite3
    db = "/THE_VAULT/jarvis/logs/events.db"
    try:
        con = sqlite3.connect(db)
        rows = con.execute(
            "SELECT source, event, details FROM events WHERE ts >= date('now', '-1 day') AND ts < date('now')"
        ).fetchall()
        con.close()
        import json
        return [{"source": r[0], "event": r[1], "details": json.loads(r[2])} for r in rows]
    except Exception as e:
        print(f"Warning: could not read events.db: {e}")
        return []


def format_events(events: list[dict]) -> str:
    if not events:
        return "(no events recorded yesterday)"
    lines = []
    for e in events:
        detail_str = ", ".join(f"{k}={v}" for k, v in e["details"].items()) if e["details"] else ""
        lines.append(f"- [{e['source']}] {e['event']}" + (f": {detail_str}" if detail_str else ""))
    return "\n".join(lines)


def summarize(events_text: str) -> str:
    if not is_healthy():
        return "(Ollama offline — summary skipped)"
    system = (
        "You are summarizing a developer's daily activity log. "
        "Write a concise summary in <=150 words. "
        "Focus on what was accomplished. Be specific. Plain prose, no bullet points."
    )
    messages = [{"role": "user", "content": f"Activity log:\n{events_text}"}]
    try:
        return chat(route("summarize"), messages, system=system, thinking=False)
    except Exception as e:
        return f"(summary failed: {e})"


def notify(summary: str) -> None:
    try:
        subprocess.run(
            ["notify-send", "-u", "normal", "☀️ Jarvis Daily Digest", summary[:200]],
            timeout=5
        )
    except Exception:
        pass


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"[Daily Digest] Generating for {today}...")

    events = get_yesterday_events()
    if not events:
        print("[Daily Digest] No events yesterday. Nothing to digest.")
        sys.exit(0)

    events_text = format_events(events)
    print(f"[Daily Digest] {len(events)} events found. Summarizing...")

    summary = summarize(events_text)

    # Append to digest file
    DIGEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DIGEST_PATH, "a") as f:
        f.write(f"\n## {today}\n\n{summary}\n")

    print(f"[Daily Digest] Written to {DIGEST_PATH}")
    notify(summary)
    emit("daily_digest", "generated", {"date": today, "events": len(events)})


if __name__ == "__main__":
    main()
