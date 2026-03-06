#!/usr/bin/env python3
"""
MVP 15 — Context Updater
/THE_VAULT/jarvis/services/context_updater.py

Queries events.db for the past 7 days of activity, synthesizes a short
"what has qwerty been working on" paragraph, and appends it to user_context.md
under a dated heading. Keeps the AI's identity context fresh automatically.

Triggered by: systemd timer jarvis-context-updater (Sunday 22:00)
"""

import os
import sys
import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/THE_VAULT/jarvis")
from lib.event_bus import emit
from lib.ollama_client import chat, is_healthy
from lib.model_router import route

CONTEXT_PATH = Path("/THE_VAULT/jarvis/config/user_context.md")


def get_week_events() -> list[dict]:
    db = "/THE_VAULT/jarvis/logs/events.db"
    try:
        con = sqlite3.connect(db)
        rows = con.execute(
            "SELECT source, event, details FROM events WHERE ts > datetime('now', '-7 days')"
        ).fetchall()
        con.close()
        return [{"source": r[0], "event": r[1], "details": json.loads(r[2])} for r in rows]
    except Exception as e:
        print(f"Warning: could not read events.db: {e}")
        return []


def format_events(events: list[dict]) -> str:
    lines = []
    for e in events:
        detail_str = ", ".join(f"{k}={v}" for k, v in e["details"].items()) if e["details"] else ""
        lines.append(f"- [{e['source']}] {e['event']}" + (f": {detail_str}" if detail_str else ""))
    return "\n".join(lines)


def synthesize_summary(events_text: str) -> str:
    if not is_healthy():
        print("[Context Updater] Ollama offline — skipping synthesis.")
        return None
    system = (
        "You are summarizing a developer's week from their system activity log. "
        "Write a single paragraph (50-150 words) describing what they worked on and accomplished. "
        "Be specific about tools, projects, and milestones. "
        "Write in third person: 'This week, qwerty...'"
    )
    messages = [{"role": "user", "content": f"Activity log:\n{events_text}"}]
    try:
        return chat(route("summarize"), messages, system=system, thinking=False)
    except Exception as e:
        print(f"[Context Updater] Synthesis failed: {e}")
        return None


def append_to_context(summary: str, week_of: str) -> None:
    """Append — NEVER overwrite — user_context.md."""
    CONTEXT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONTEXT_PATH, "a") as f:
        f.write(f"\n## Week of {week_of}\n\n{summary}\n")
    print(f"[Context Updater] Appended to {CONTEXT_PATH}")


def main():
    week_of = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"[Context Updater] Running for week ending {week_of}...")

    events = get_week_events()
    if not events:
        print("[Context Updater] No events in past 7 days. Exiting.")
        sys.exit(0)

    print(f"[Context Updater] {len(events)} events found. Synthesizing summary...")
    events_text = format_events(events)
    summary = synthesize_summary(events_text)

    if summary:
        append_to_context(summary, week_of)
        emit("context_updater", "context_updated", {"week_of": week_of, "events": len(events)})
        print("[Context Updater] Done.")
        sys.exit(0)
    else:
        print("[Context Updater] No summary generated.")
        sys.exit(1)


if __name__ == "__main__":
    main()
