import subprocess
import os
import argparse
from typing import List, Optional
from lib.ollama_client import chat
from lib.model_router import route
from lib.event_bus import emit

# /home/qwerty/NixOSenv/Jarvis/lib/git_summarizer.py

def get_git_diff(repo_path: str, since: str = "HEAD~1") -> str:
    """Returns the git diff for the given repository and range."""
    try:
        # Safety: list-form arguments and timeout as per spec
        cmd = ["git", "-C", repo_path, "diff", since, "HEAD"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Git diff failed: {e.stderr}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("Git diff timed out")

def summarize_diff(diff_text: str) -> str:
    """Uses LLM to summarize a git diff."""
    if not diff_text.strip():
        return "No changes detected."
        
    prompt = f"""Summarize the following git diff concisely. Focus on:
1. Significant logic changes.
2. New files or deleted files.
3. Potential breaking changes.

DIFF:
{diff_text[:8000]} # Truncate if too large
"""
    try:
        return chat(route('summarize'), [{'role': 'user', 'content': prompt}])
    except Exception as e:
        emit('git_summarizer', 'error', {'error': str(e)}, level='ERROR')
        raise

def main():
    parser = argparse.ArgumentParser(description="Summarize recent Git changes.")
    parser.add_argument("repo", help="Path to the git repository")
    parser.add_argument("--since", default="HEAD~1", help="Git revision range (default: HEAD~1)")
    
    args = parser.parse_args()
    repo_path = os.path.abspath(args.repo)
    
    emit('git_summarizer', 'started', {'repo': repo_path, 'since': args.since})
    
    try:
        diff = get_git_diff(repo_path, args.since)
        summary = summarize_diff(diff)
        
        print("\n--- Recent Changes Summary ---")
        print(summary)
        
        emit('git_summarizer', 'completed', {'repo': repo_path})
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import sys
    main()
