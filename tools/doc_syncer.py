#!/usr/bin/env python3
"""
Jarvis Auto-Doc Syncer
/home/qwerty/NixOSenv/Jarvis/tools/doc_syncer.py

Scans code files for features/commands and ensures documentation is up to date.
"""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, "/THE_VAULT/jarvis")
from lib.ollama_client import chat
from lib.model_router import route

# Configuration
REPO_ROOT = Path("/home/qwerty/NixOSenv/Jarvis")
DOCS_TO_SYNC = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs/OPTIMIZATION_ROADMAP.md",
]
CODE_FILES = [
    REPO_ROOT / "jarvis.py",
    REPO_ROOT / "services/coding_agent.py",
]

def extract_features():
    features = []
    
    # Extract CLI commands from jarvis.py
    if (REPO_ROOT / "jarvis.py").exists():
        content = (REPO_ROOT / "jarvis.py").read_text()
        # Look for argparse or simple command mappings
        commands = re.findall(r'# command: (\w+) - (.+)', content)
        for cmd, desc in commands:
            features.append(f"CLI Command: {cmd} - {desc}")

    # Extract HTTP endpoints from coding_agent.py
    if (REPO_ROOT / "services/coding_agent.py").exists():
        content = (REPO_ROOT / "services/coding_agent.py").read_text()
        endpoints = re.findall(r'elif self\.path == "(/[^"]+)":', content)
        for ep in endpoints:
            features.append(f"HTTP Endpoint: {ep}")
            
    return features

def sync_doc(doc_path, features):
    if not doc_path.exists():
        return
        
    doc_content = doc_path.read_text()
    
    # Check for missing features
    missing = [f for f in features if f.split(":")[1].strip().split(" ")[0] not in doc_content]
    
    if not missing:
        print(f"[Doc-Sync] {doc_path.name} is up to date.")
        return

    print(f"[Doc-Sync] Found {len(missing)} missing features in {doc_path.name}.")
    
    system = "You are a technical writer. Update the provided markdown documentation to include the new features listed. Keep the style consistent."
    prompt = f"Markdown Content:\n{doc_content}\n\nNew Features to add:\n" + "\n".join(missing)
    
    try:
        updated_content = chat(route("summarize"), [{"role": "user", "content": prompt}], system=system, thinking=False)
        if updated_content and len(updated_content) > 100:
            doc_path.write_text(updated_content)
            print(f"[Doc-Sync] Successfully updated {doc_path.name}.")
    except Exception as e:
        print(f"[Doc-Sync] Failed to update {doc_path.name}: {e}")

def main():
    print("[Doc-Sync] Starting synchronization...")
    features = extract_features()
    if not features:
        print("[Doc-Sync] No features found to sync.")
        return
        
    for doc in DOCS_TO_SYNC:
        sync_doc(doc, features)

if __name__ == "__main__":
    main()
