#!/usr/bin/env python3
"""
Jarvis Web UI (Phase 7.4)
/home/qwerty/NixOSenv/Jarvis/services/web_ui.py

FastAPI dashboard for Jarvis system status, events, and Knowledge Graph.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# Runtime paths
BASE_DIR = Path(os.environ.get("JARVIS_ROOT", Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(BASE_DIR))

try:
    from lib.event_bus import query_today
    from lib.knowledge_graph import KnowledgeGraph
except ImportError:
    # Fallback for direct execution
    sys.path.append(os.getcwd())
    from lib.event_bus import query_today
    from lib.knowledge_graph import KnowledgeGraph

app = FastAPI(title="Jarvis Dashboard")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Mount static files if directory exists
static_path = BASE_DIR / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    try:
        events = query_today()
    except Exception as e:
        print(f"Error querying events: {e}")
        events = []
    return templates.TemplateResponse("index.html", {"request": request, "events": events[:20]})

@app.get("/api/events", response_class=HTMLResponse)
async def get_events_html(request: Request):
    """Returns HTML snippet for HTMX polling."""
    try:
        events = query_today()[:30]
    except Exception as e:
        print(f"Error querying events: {e}")
        events = []
        
    html = ""
    for event in events:
        level_class = f"level-{event['level'].lower()}"
        ts = event['ts'].split('T')[1][:8] if 'T' in event['ts'] else event['ts']
        html += f"""
        <div class="event-item {level_class}">
            <span class="ts">{ts}</span>
            <span class="source">[{event['source']}]</span>
            <span class="msg">{event['event']}</span>
        </div>
        """
    return HTMLResponse(content=html)

@app.get("/api/graph")
async def get_graph():
    try:
        kg = KnowledgeGraph()
        return kg.get_recent_relations(limit=100)
    except Exception as e:
        return {"error": str(e)}

@app.get("/health")
async def health():
    return {"status": "online", "timestamp": datetime.now(timezone.utc).isoformat()}

if __name__ == "__main__":
    port = int(os.environ.get("JARVIS_UI_PORT", 8000))
    print(f"Starting Jarvis Web UI on http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
