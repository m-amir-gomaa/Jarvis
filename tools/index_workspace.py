import os
import sys
import argparse
import json
from pathlib import Path
from lib.knowledge_manager import KnowledgeManager
from lib.event_bus import emit

# /THE_VAULT/jarvis/tools/index_workspace.py

class WorkspaceIndexer:
    def __init__(self):
        self.km = KnowledgeManager()

    def index_directory(self, target_dir: str, category: str):
        target_path = Path(target_dir).absolute()
        if not target_path.exists():
            print(f"[Indexer] Error: {target_dir} not found.")
            return False

        print(f"[Indexer] Scanning {target_path} for category '{category}'...")
        
        # Simple recursive scan
        # For MVP, we only take common text-based source files
        extensions = {'.py', '.rs', '.js', '.ts', '.c', '.cpp', '.h', '.nix', '.md', '.txt', '.lua'}
        
        files_indexed = 0
        for root, dirs, files in os.walk(target_path):
            # Skip hidden dirs (like .git)
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in extensions:
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        if not content.strip():
                            continue
                            
                        # Store in Knowledge DB (Layer 2: Domain)
                        # Metadata helps differentiate between different codebases
                        metadata = {
                            "category": category,
                            "rel_path": str(file_path.relative_to(target_path)),
                            "type": "source_code"
                        }
                        
                        self.km.add_entry(
                            layer=2,
                            content=content,
                            source_url=str(file_path),
                            source_title=file,
                            category=category,
                            metadata=metadata
                        )
                        files_indexed += 1
                    except Exception as e:
                        print(f"  [Indexer] Failed to read {file}: {e}")

        print(f"[Indexer] Successfully indexed {files_indexed} files.")
        emit("indexer", "completed", {"directory": str(target_path), "count": files_indexed, "category": category})
        return True

def main():
    parser = argparse.ArgumentParser(description="Jarvis Workspace Indexer")
    parser.add_argument("directory", nargs="?", default=".", help="Directory to index (default: current)")
    parser.add_argument("--category", "-c", required=True, help="Domain category name (e.g. 'jarvis_core', 'webapp')")
    args = parser.parse_args()

    indexer = WorkspaceIndexer()
    success = indexer.index_directory(args.directory, args.category)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
