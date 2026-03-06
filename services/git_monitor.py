import time
import os
import subprocess
from lib.event_bus import emit
from lib.git_summarizer import get_git_diff, summarize_diff

# /THE_VAULT/jarvis/services/git_monitor.py

REPO_PATH = "/home/qwerty/NixOSenv"
CHECK_INTERVAL = 3600  # 1 hour

def check_for_changes():
    """Checks for new commits and emits summaries."""
    try:
        # Get last checked commit or use HEAD~1
        last_commit_path = "/THE_VAULT/jarvis/logs/last_commit.txt"
        since = "HEAD~1"
        if os.path.exists(last_commit_path):
            with open(last_commit_path, "r") as f:
                since = f.read().strip()
        
        # Get current HEAD
        head_cmd = ["git", "-C", REPO_PATH, "rev-parse", "HEAD"]
        current_head = subprocess.check_output(head_cmd, text=True, timeout=30).strip()
        
        if current_head == since:
            return # No new changes
            
        emit('git_monitor', 'changes_detected', {'repo': REPO_PATH, 'range': f"{since}..HEAD"})
        
        diff = get_git_diff(REPO_PATH, since)
        if diff.strip():
            summary = summarize_diff(diff)
            emit('git_monitor', 'summary_generated', {'repo': REPO_PATH, 'summary': summary})
            print(f"Summary for {REPO_PATH}:\n{summary}")
        
        # Update last commit
        with open(last_commit_path, "w") as f:
            f.write(current_head)
            
    except Exception as e:
        emit('git_monitor', 'error', {'error': str(e)}, level='ERROR')
        print(f"Error checking git changes: {e}")

def main():
    print(f"Jarvis Git Monitor starting for {REPO_PATH}...")
    while True:
        check_for_changes()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
