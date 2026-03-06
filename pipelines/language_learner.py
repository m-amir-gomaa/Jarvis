#!/usr/bin/env python3
"""
Jarvis Language Learner Pipeline
/home/qwerty/NixOSenv/Jarvis/pipelines/language_learner.py

Orchestrates the assisted process of learning a new programming language.
Stages: Discovery -> Core Ingestion -> Resource Research -> Inbox Integration.
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path
from lib.event_bus import emit

BASE_DIR = Path("/home/qwerty/NixOSenv/Jarvis")
VENV_PY = str(BASE_DIR / ".venv" / "bin" / "python")
PYTHONPATH = str(BASE_DIR)

def run_pipeline(cmd, env=None):
    if env is None:
        env = {**os.environ, "PYTHONPATH": PYTHONPATH}
    result = subprocess.run(cmd, env=env, text=True)
    return result.returncode == 0

def confirm(prompt_msg):
    print(f"\n[Learner] {prompt_msg}")
    choice = input("Confirm? [Y/n]: ").strip().lower()
    return choice in ('', 'y', 'yes')

def main():
    parser = argparse.ArgumentParser(description="Jarvis Language Learner Orchestrator")
    parser.add_argument("--query", "-q", required=True, help="Topic/Language to learn")
    args = parser.parse_args()

    topic = args.query
    emit("language_learner", "started", {"topic": topic})
    print(f"=== Jarvis Assisted Learning: {topic} ===")

    # STAGE 1: Documentation Discovery
    print(f"\n[Stage 1] Searching for official documentation for {topic}...")
    research_cmd = [VENV_PY, str(BASE_DIR / "pipelines" / "research_agent.py"), "--query", f"official {topic} programming language documentation", "--sources", "3"]
    run_pipeline(research_cmd)
    
    # We don't have a direct way to get the output from research_agent.py easily here without parsing files,
    # but the user can see the output.
    
    doc_url = input(f"\n[Action Required] Please paste the official documentation URL for {topic} to begin scraping (or press Enter to skip if you want to paste it later): ").strip()
    
    if doc_url:
        print(f"\n[Stage 2] Starting core ingestion for {doc_url} (Layer 1 & 2)...")
        # Ingest into Layer 2 (Standard Docs)
        learn_cmd = [VENV_PY, str(BASE_DIR / "pipelines" / "doc_learner.py"), doc_url, "--layer", "2", "--category", f"{topic.lower()}_docs"]
        run_pipeline(learn_cmd)
    else:
        print("[Skipped] Core documentation scraping skipped.")

    # STAGE 3: Resource Research (Reddit/Forums)
    print(f"\n[Stage 3] Searching for highly-praised {topic} resources on Reddit and forums...")
    forum_query = f"best books and resources for learning {topic} reddit forums"
    forum_research_cmd = [VENV_PY, str(BASE_DIR / "pipelines" / "research_agent.py"), "--query", forum_query, "--deep", "--sources", "5"]
    run_pipeline(forum_research_cmd)

    print(f"\n[Stage 4] Adding manual research to Inbox...")
    # This is a placeholder for a more automated extraction in the future
    # For now, it encourages the user to check the research results and add to inbox if not auto-detected.
    
    print("\n=== Learning Process Summary ===")
    print(f"1. Core Docs: Attempted ingestion of {doc_url if doc_url else 'N/A'}")
    print(f"2. Research: Conducted forum search for {topic} materials.")
    print("3. Next Steps: Check 'jarvis inbox' for recommended reading.")
    print("4. Deep Dive: Place any acquired books (PDF/MD) in ~/Downloads/JarvisMaterials for Layer 3 ingestion.")
    
    emit("language_learner", "completed", {"topic": topic})

if __name__ == "__main__":
    main()
