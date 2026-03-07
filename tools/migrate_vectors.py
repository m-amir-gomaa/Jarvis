import sys
import os
from pathlib import Path

# Ensure Jarvis root is in PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.semantic_memory import SemanticMemory

def main():
    print("Starting sqlite-vec migration...")
    sm = SemanticMemory()
    sm.migrate_from_blob()
    
if __name__ == "__main__":
    main()
