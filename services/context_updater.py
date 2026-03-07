#!/usr/bin/env python3
import sqlite3
import time
import os
from pathlib import Path
import sys

# /home/qwerty/NixOSenv/Jarvis/services/context_updater.py

# Add JARVIS_ROOT to sys.path to allow imports
JARVIS_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(JARVIS_ROOT))

from lib.llm import ask, Privacy

def update_context():
    db_path = JARVIS_ROOT / "logs" / "events.db"
    if not db_path.exists():
        print(f"No events.db found at {db_path}.")
        return

    # Last 7 days
    week_ago = int(time.time()) - (7 * 24 * 3600)
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM events WHERE ts > ? ORDER BY ts ASC", (week_ago,)).fetchall()
        conn.close()
    except Exception as e:
        print(f"Error reading events: {e}")
        return

    if not rows:
        print("No recent events to process.")
        # Create a basic context if empty
        summary = "No significant activities recorded this week. Jarvis is standing by."
    else:
        events_text = ""
        for r in rows:
            events_text += f"- [{r['source']}] {r['event']}\n"

        prompt = f"""Summarize the following recent events into a concise paragraph (3-4 sentences) describing the user's focus and progress for this week. 
This will be used as a 'Long-Term Memory' context for the AI. Look for patterns in coding, learning, or system configuration.

Events:
{events_text}

Summary:"""

        print(f"Synthesizing context from {len(rows)} events...")
        summary = ask(task="reason", privacy=Privacy.INTERNAL, messages=[{"role": "user", "content": prompt}], thinking=False)
    
    context_path = JARVIS_ROOT / "docs" / "user_context.md"
    
    header = f"# User Context (Updated {time.strftime('%Y-%m-%d %H:%M:%S')})\n\n"
    
    try:
        with open(context_path, "w") as f:
            f.write(header + summary.strip() + "\n")
        print(f"Context updated successfully in {context_path}")
    except Exception as e:
        print(f"Error writing context: {e}")

if __name__ == "__main__":
    update_context()
