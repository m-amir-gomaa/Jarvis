import asyncio
import os
import subprocess
import signal
from pathlib import Path
from typing import Optional

from lib.event_bus import emit
from lib.git_summarizer import get_git_diff, summarize_diff

# /home/qwerty/NixOSenv/Jarvis/services/git_monitor.py

_JARVIS_ROOT = Path(os.environ.get("JARVIS_ROOT", Path(__file__).resolve().parent.parent))
REPO_PATH    = str(_JARVIS_ROOT.parent)
LAST_COMMIT_PATH = str(_JARVIS_ROOT / "logs" / "last_commit.txt")
CHECK_INTERVAL = 3600  # 1 hour

async def check_for_changes():
    """Checks for new commits and emits summaries."""
    try:
        # Get last checked commit or use HEAD~1
        since = "HEAD~1"
        if os.path.exists(LAST_COMMIT_PATH):
            with open(LAST_COMMIT_PATH, "r") as f:
                since = f.read().strip()
        
        # Get current HEAD
        process = await asyncio.create_subprocess_exec(
            "git", "-C", REPO_PATH, "rev-parse", "HEAD",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"Git rev-parse failed: {stderr.decode()}")
            
        current_head = stdout.decode().strip()
        
        if current_head == since:
            return # No new changes
            
        emit('git_monitor', 'changes_detected', {'repo': REPO_PATH, 'range': f"{since}..HEAD"})
        
        # Wrap blocking ops in executor
        loop = asyncio.get_running_loop()
        diff = await loop.run_in_executor(None, get_git_diff, REPO_PATH, since)
        
        if diff.strip():
            summary = await loop.run_in_executor(None, summarize_diff, diff)
            emit('git_monitor', 'summary_generated', {'repo': REPO_PATH, 'summary': summary})
            print(f"Summary for {REPO_PATH}:\n{summary}")
        
        # Update last commit
        with open(LAST_COMMIT_PATH, "w") as f:
            f.write(current_head)
            
    except Exception as e:
        emit('git_monitor', 'error', {'error': str(e)}, level='ERROR')
        print(f"Error checking git changes: {e}")

async def main():
    print(f"Jarvis Git Monitor (Async) starting for {REPO_PATH}...")
    
    stop_event = asyncio.Event()

    def handle_exit():
        print("Shutdown signal received.")
        stop_event.set()

    # Register signal handlers
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_exit)

    while not stop_event.is_set():
        await check_for_changes()
        try:
            from lib.prefs_manager import PrefsManager
            pm = PrefsManager()
            interval = pm.get("services.git_monitor.check_interval_sec", 3600)
            # Wait for interval OR until stop event is set
            await asyncio.wait_for(stop_event.wait(), timeout=float(interval))
        except asyncio.TimeoutError:
            pass # Continue loop

if __name__ == "__main__":
    asyncio.run(main())
