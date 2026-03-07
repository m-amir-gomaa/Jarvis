import os
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(os.environ.get("JARVIS_ROOT", "/home/qwerty/NixOSenv/Jarvis"))
DIGEST_PATH = BASE_DIR / "logs" / "daily_digest.md"
EVENTS_DB = BASE_DIR / "logs" / "events.db"

sys.path.insert(0, str(BASE_DIR))
from lib.event_bus import emit
from lib.ollama_client import is_healthy
from lib.llm import ask, Privacy


def get_yesterday_events() -> list[dict]:
    import sqlite3
    try:
        con = sqlite3.connect(str(EVENTS_DB))
        rows = con.execute(
            "SELECT source, event, details FROM events WHERE ts >= datetime('now', '-1 day')"
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
        
    # NEW: Pull recent Knowledge Graph relations for context
    graph_context = ""
    try:
        from lib.knowledge_graph import KnowledgeGraph
        kg = KnowledgeGraph()
        G = kg.build_graph(limit=20)
        relations = []
        for u, v, data in G.edges(data=True):
            relations.append(f"- {u} --[{data.get('relation')}]--> {v}")
        if relations:
            graph_context = "### RECENT KNOWLEDGE GRAPH RELATIONS\n" + "\n".join(relations)
    except Exception as e:
        print(f"Warning: could not read knowledge graph: {e}")

    system = (
        "You are summarizing a developer's daily activity log and newly extracted knowledge. "
        "Write a concise summary in <=150 words. "
        "Focus on what was accomplished and what facts were learned. "
        "Be specific. Plain prose, no bullet points."
    )
    prompt = f"{graph_context}\n\nActivity log:\n{events_text}"
    messages = [{"role": "user", "content": prompt}]
    try:
        return ask(task="summarize", privacy=Privacy.INTERNAL, messages=messages, system=system, thinking=False)
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
