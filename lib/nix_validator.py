import subprocess
import os
import argparse
import sys
from typing import List, Tuple
from lib.event_bus import emit

# /THE_VAULT/jarvis/lib/nix_validator.py

def run_nix_instantiate(file_path: str) -> Tuple[bool, str]:
    """Runs nix-instantiate to check for syntax/eval errors."""
    try:
        cmd = ["nix-instantiate", "--parse", file_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return True, "Syntax OK"
        else:
            return False, result.stderr
    except Exception as e:
        return False, str(e)

def check_for_unsafe_patterns(file_path: str) -> List[str]:
    """Scans for patterns that might be risky or require attention."""
    warnings = []
    try:
        with open(file_path, "r") as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                # Example: checking for hardcoded secrets or undesirable patterns
                if "password =" in line.lower() and not "config.sops" in line:
                    warnings.append(f"L{i+1}: Potential hardcoded password detected.")
                if "allowUnfree = true" in line:
                    # just a note, not an error
                    pass
    except Exception as e:
        warnings.append(f"Error reading file: {e}")
    return warnings

def validate_config(file_path: str):
    """Full validation suite."""
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        sys.exit(1)
        
    emit('nix_validator', 'started', {'file': file_path})
    print(f"Validating {file_path}...")
    
    # 1. Nix Syntax
    ok, msg = run_nix_instantiate(file_path)
    if not ok:
        print(f"  [FAIL] Nix Syntax/Eval: {msg}")
        emit('nix_validator', 'syntax_failed', {'error': msg}, level='ERROR')
        sys.exit(1)
    else:
        print("  [OK] Nix Syntax")
        
    # 2. Pattern Matching
    warnings = check_for_unsafe_patterns(file_path)
    if warnings:
        for w in warnings:
            print(f"  [WARN] {w}")
        emit('nix_validator', 'warnings_found', {'count': len(warnings)})
    else:
        print("  [OK] Pattern checks")
        
    emit('nix_validator', 'completed', {'file': file_path})
    print("Validation successful.")

def main():
    parser = argparse.ArgumentParser(description="Validate NixOS configuration files.")
    parser.add_argument("file", help="Path to the .nix file")
    args = parser.parse_args()
    
    validate_config(os.path.abspath(args.file))

if __name__ == "__main__":
    main()
