#!/usr/bin/env python3
"""
MVP 8 — Research Agent
/THE_VAULT/jarvis/pipelines/research_agent.py

Searches SearXNG (localhost:8888) for a query, fetches top results,
summarizes findings via Qwen3-14B, and saves to /THE_VAULT/jarvis/research/.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, "/THE_VAULT/jarvis")
from lib.event_bus import emit
from lib.model_router import route
from lib.ollama_client import chat, is_healthy

SEARXNG_URL = os.getenv("SEARXNG_URL", "http://localhost:8888")
RESEARCH_DIR = Path("/THE_VAULT/jarvis/research")


TECH_KEYWORDS = {
    "rust", "python", "javascript", "lua", "nix", "nixos", "framework", "api", "library",
    "docker", "kubernetes", "git", "linux", "kernel", "compile", "debug", "error", "code",
    "programming", "software", "database", "sql", "nosql", "cloud", "aws", "azure", "gcp"
}

def detect_research_category(query: str) -> str:
    """Detect if the query is technical (coding/IT) or general."""
    q_lower = query.lower()
    if any(k in q_lower for k in TECH_KEYWORDS):
        return "it"
    # Fallback to model-based detection for nuanced queries if needed
    return "general"

def search_searxng(query: str, num_results: int = 7) -> list[dict]:
    """Query SearXNG JSON API using specialized categories."""
    category = detect_research_category(query)
    print(f"[Research] Using engine: {category}")
    
    try:
        resp = requests.get(
            f"{SEARXNG_URL}/search",
            params={"q": query, "format": "json", "categories": category},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])[:num_results]
    except Exception as e:
        print(f"[Research] SearXNG search failed: {e}", file=sys.stderr)
        return []


def fetch_snippet(result: dict) -> str:
    """Extract meaningful content from a search result."""
    return result.get("content", result.get("title", ""))


def summarize_results(query: str, results: list[dict], deep: bool = False, category: str = "general") -> str:
    """Summarize search results via Qwen3 (8B or 14B if deep)."""
    if not results:
        return "No results found."
    if not is_healthy():
        return "(Ollama offline — raw results only)"

    # Reduced snippet size for sub-2.5min CPU performance
    snippets = "\n\n".join(
        f"Source: {r.get('url', 'unknown')}\nTitle: {r.get('title')}\n{fetch_snippet(r)[:1000]}"
        for r in results
    )
    
    if category == "it":
        system = (
            "You are a Senior Software Architect. Provide a concise technical analysis. "
            "Focus on implementation, performance, and compatibility. "
            "Prioritize code names and key features. Be precise and brief."
        )
    else:
        system = (
            "You are a Research Analyst. Provide a concise synthesis of findings. "
            "Use bullet points. Focus on key takeaways. Be informative but brief."
        )
    
    messages = [{"role": "user", "content": f"Research Topic: {query}\n\nSearch raw data:\n{snippets}"}]
    try:
        model_task = "reason" if deep else "summarize"
        # Reduced num_ctx to 4096 for CPU speed stability
        return chat(route(model_task), messages, system=system, thinking=deep, num_ctx=4096)
    except Exception as e:
        return f"(summarization failed: {e})\n\nRaw snippets:\n{snippets}"


def save_research(query: str, summary: str, results: list[dict]) -> Path:
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    slug = query.lower().replace(" ", "_")[:40]
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_path = RESEARCH_DIR / f"{ts}_{slug}.md"
    with open(out_path, "w") as f:
        f.write(f"# Research: {query}\n\n")
        f.write(f"*Generated: {ts}*\n\n")
        f.write(f"## Summary\n\n{summary}\n\n")
        f.write("## Sources\n\n")
        for r in results:
            f.write(f"- [{r.get('title', 'untitled')}]({r.get('url', '')})\n")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Jarvis Research Agent (MVP 8)")
    parser.add_argument("--query", "-q", required=True, help="Research query")
    parser.add_argument("--sources", "-n", type=int, default=5, help="Number of sources")
    parser.add_argument("--deep", action="store_true", help="Use 14B thinking model for synthesis")
    args = parser.parse_args()

    category = detect_research_category(args.query)
    print(f"[Research] Searching: '{args.query}' using {category} engine...")
    results = search_searxng(args.query, args.sources)

    if not results:
        print(f"[Research] No results from SearXNG ({category}). Is it running on :8888?")
        sys.exit(1)

    print(f"[Research] {len(results)} results. Summarizing as {category}...")
    summary = summarize_results(args.query, results, deep=args.deep, category=category)

    out = save_research(args.query, summary, results)
    print(f"[Research] Saved to: {out}")
    print(f"\n--- Summary ---\n{summary}")

    emit("research_agent", "completed", {"query": args.query, "sources": len(results), "file": str(out)})


if __name__ == "__main__":
    main()
