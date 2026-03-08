#!/usr/bin/env python3
"""
Jarvis Speculative Refactor Pipeline
/home/qwerty/NixOSenv/Jarvis/pipelines/speculative_refactor.py

Wraps a refactoring task in a snapshot/restore sandbox.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Callable, Optional

# Ensure project root is in sys.path
BASE_DIR = Path(os.environ.get("JARVIS_ROOT", Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(BASE_DIR))

from lib.snapshot_manager import SnapshotManager
from lib.event_bus import emit

def run_speculative(
    task_name: str,
    refactor_func: Callable[[], bool],
    test_cmd: Optional[str] = None,
    vault_root: Optional[Path] = None
) -> bool:
    """
    Run a refactoring task speculatively.
    
    Args:
        task_name: A label for the snapshot.
        refactor_func: A callback that performs the refactor. Should return True on success.
        test_cmd: A shell command to run tests. Returns success if exit code is 0.
        vault_root: Path to the vault. Defaults to BASE_DIR.
        
    Returns:
        True if refactor and tests succeeded, False otherwise (with rollback).
    """
    if vault_root is None:
        vault_root = BASE_DIR
        
    sm = SnapshotManager(vault_root)
    
    print(f"[Speculative] Creating pre-refactor snapshot for '{task_name}'...")
    snapshot_path = sm.create_snapshot(label=f"speculative_{task_name}")
    snapshot_name = snapshot_path.name
    
    success = False
    try:
        print(f"[Speculative] Executing refactor function...")
        if not refactor_func():
            print(f"[Speculative] Refactor function reported failure.")
            raise Exception("Refactor function failed")
            
        if test_cmd:
            print(f"[Speculative] Running tests: {test_cmd}")
            res = subprocess.run(test_cmd, shell=True, capture_output=True, text=True)
            if res.returncode != 0:
                print(f"[Speculative] Tests failed:\n{res.stdout}\n{res.stderr}")
                emit("speculative_refactor", "test_failure", {"task": task_name, "output": res.stdout})
                raise Exception("Tests failed")
        
        print(f"[Speculative] Refactor successful. Persisting changes.")
        emit("speculative_refactor", "success", {"task": task_name})
        success = True
        
    except Exception as e:
        print(f"[Speculative] Error occurred: {e}. Rolling back...")
        emit("speculative_refactor", "rollback_initiated", {"task": task_name, "error": str(e)})
        if sm.restore_snapshot(snapshot_name):
            print(f"[Speculative] Rollback complete.")
        else:
            print(f"[Speculative] CRITICAL: Failed to restore snapshot {snapshot_name}")
            emit("speculative_refactor", "restore_failed", {"task": task_name, "snapshot": snapshot_name})
            
    finally:
        # cleanup snapshot file regardless of success (unless we want to keep them)
        # For now, let's keep them in the snapshots/ dir as per SnapshotManager logic.
        pass
        
    return success

if __name__ == "__main__":
    # Simple CLI test if run directly
    def dummy_refactor():
        print("Doing dummy work...")
        with open(BASE_DIR / "dummy_file.txt", "w") as f:
            f.write("speculative content")
        return True
        
    run_speculative("test_run", dummy_refactor, test_cmd="ls dummy_file.txt")
