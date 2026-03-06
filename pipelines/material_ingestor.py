#!/usr/bin/env python3
import os
import sys
import time
import shutil
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# /home/qwerty/NixOSenv/Jarvis/pipelines/material_ingestor.py

BASE_DIR = Path("/home/qwerty/NixOSenv/Jarvis")
VAULT_DIR = Path("/THE_VAULT/jarvis")
DOWNLOADS_DIR = Path("/home/qwerty/Downloads/JarvisMaterials")
VENV_PY = "/THE_VAULT/jarvis/.venv/bin/python"

def run_command(cmd, input_str=None):
    """Runs a command and handles user confirmation if needed."""
    print(f"[Ingestor] Running: {' '.join(cmd)}")
    try:
        if input_str:
            result = subprocess.run(cmd, input=input_str, capture_output=True, text=True, check=True)
        else:
            # We use check=False to capture output and handle errors manually
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"[Ingestor] Warning: Cmd failed (RC {result.returncode}): {result.stderr}")
        return result.stdout
    except Exception as e:
        print(f"[Ingestor] Error running command: {e}")
        return None

def confirm(prompt_msg):
    """Wait for user confirmation."""
    print(f"\n[Ingestor] {prompt_msg}")
    choice = input("Proceed? [y/N]: ").strip().lower()
    return choice == 'y'

def detect_language(file_path):
    """Simple heuristic for language detection based on path or content keywords."""
    path_lower = str(file_path).lower()
    if "python" in path_lower or ".py" in path_lower: return "python"
    if "rust" in path_lower or ".rs" in path_lower: return "rust"
    if "javascript" in path_lower or "node" in path_lower or ".js" in path_lower: return "javascript"
    if "nix" in path_lower: return "nix"
    if "lua" in path_lower: return "lua"
    return "general_coding"

def process_material(file_path):
    """Smart conversion: detect PDF -> convert to MD."""
    file_path = Path(file_path)
    print(f"\n--- Processing: {file_path.name} ---")
    
    if not confirm(f"Convert and index '{file_path.name}'?"):
        print("Skipping.")
        return

    # 1. Detection and Conversion
    # We call doc_converter.py which handles both Pandoc and MinerU
    print(f"[Ingestor] Converting {file_path.name}...")
    is_pdf = file_path.suffix.lower() == ".pdf"
    
    # Run doc_converter.py
    # /THE_VAULT/jarvis/tools/doc_converter.py <input> --cleanup
    conv_cmd = [VENV_PY, str(VAULT_DIR / "tools" / "doc_converter.py"), str(file_path), "--cleanup"]
    md_output_path_str = run_command(conv_cmd)
    
    if not md_output_path_str:
        print(f"[Ingestor] Conversion failed for {file_path.name}")
        return

    md_path = Path(md_output_path_str.strip().split("\n")[-1]) # Grab the last line (the path)
    if not md_path.exists():
        print(f"[Ingestor] MD file not found at: {md_path}")
        return

    # 2. Language Detection
    category = detect_language(file_path)
    print(f"[Ingestor] Detected category: {category}")

    # 3. Indexing
    # We use doc_learner.py to index into Layer 3 (Theory) by default for books/docs
    print(f"[Ingestor] Indexing {file_path.name} into knowledge base...")
    learn_cmd = [VENV_PY, str(BASE_DIR / "pipelines" / "doc_learner.py"), str(md_path), "--layer", "3", "--category", category]
    run_command(learn_cmd)
    
    # Cleanup MD after indexing to save space
    if md_path != file_path:
        md_path.unlink()
        print(f"[Ingestor] Cleaned up intermediate MD: {md_path.name}")

def main():
    parser = argparse.ArgumentParser(description="Advanced Material Ingestor")
    parser.add_argument("--query", "-q", required=True, help="Topic for research and indexing")
    args = parser.parse_args()

    # Step 1: Extensive Research
    print(f"[Ingestor] Starting research on: \"indexing strategies for {args.query} documentation and books\"")
    research_cmd = [VENV_PY, str(BASE_DIR / "pipelines" / "research_agent.py"), "--query", f"indexing layers for {args.query} coding documentation and books", "--deep"]
    research_output = run_command(research_cmd)
    
    # Step 2: List Results and Confirm
    if not confirm("Research results listed above. Proceed to index found documentation and wait for books?"):
        print("Ingestor task stopped.")
        return

    # Step 3: Wait for materials in ~/Downloads/JarvisMaterials
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n[Ingestor] Waiting for materials in: {DOWNLOADS_DIR}")
    print("Please place books/documentation in that folder. Monitoring...")
    
    try:
        while True:
            files = list(DOWNLOADS_DIR.iterdir())
            processed_marker = DOWNLOADS_DIR / ".processed"
            processed_marker.touch() # Ensure it exists
            
            with open(processed_marker, "r") as f:
                processed_files = set(f.read().splitlines())
            
            new_files = [f for f in files if f.name not in processed_files and not f.name.startswith(".")]
            
            for f in new_files:
                process_material(f)
                with open(processed_marker, "a") as log:
                    log.write(f.name + "\n")
                print(f"[Ingestor] Finished processing {f.name}")
            
            if not new_files:
                time.sleep(10) # Wait 10 seconds before next check
                sys.stdout.write(".")
                sys.stdout.flush()
    except KeyboardInterrupt:
        print("\n[Ingestor] Stopping wait loop.")

if __name__ == "__main__":
    main()
