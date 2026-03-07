#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

# Try to use tomllib (Python 3.11+) or fall back to a manual writer for simple cases
try:
    import tomllib
except ImportError:
    tomllib = None

def migrate(v1_path: Path, v2_path: Path):
    if not v1_path.exists():
        print(f"Error: v1 config not found at {v1_path}")
        return

    print(f"Migrating {v1_path} -> {v2_path}...")
    
    with open(v1_path, "r") as f:
        v1_data = json.load(f)
    
    # Plausible v1 structure: {"modes": {"coder": {"model": "...", "temp": 0.2}, ...}}
    # Jarvis v2 expects: [modes.coder] \n model = "..." \n ...
    
    v2_content = "# Jarvis v2 Modes (Migrated from v1)\n\n"
    
    modes = v1_data.get("modes", v1_data) # handle both wrapped and raw dicts
    
    for mode_name, settings in modes.items():
        v2_content += f"[modes.{mode_name}]\n"
        for key, value in settings.items():
            if isinstance(value, str):
                v2_content += f'{key} = "{value}"\n'
            elif isinstance(value, bool):
                v2_content += f'{key} = {"true" if value else "false"}\n'
            else:
                v2_content += f'{key} = {value}\n'
        v2_content += "\n"
    
    v2_path.parent.mkdir(parents=True, exist_ok=True)
    with open(v2_path, "w") as f:
        f.write(v2_content)
    
    print("Migration complete.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: migrate_modes.py <v1_json_path> <v2_toml_path>")
        sys.exit(1)
    
    migrate(Path(sys.argv[1]), Path(sys.argv[2]))
