import os
import json
import hashlib
import argparse
import sys
from typing import List, Dict, Optional
from lib.llm import ask
from lib.model_router import Privacy
from lib.event_bus import emit

# /home/qwerty/NixOSenv/Jarvis/tools/cleaner.py

DEFAULT_PROMPT = """You are a document preparation assistant. Clean and optimise this Markdown for upload to NotebookLM. NotebookLM is text-only.

REMOVE: image tags ![...](...), dead figure references (Fig. N, See diagram), page number echoes, running headers/footers, orphaned footnote markers, full reference lists at end of document, index sections, TOC pages, repeated copyright boilerplate.

PRESERVE: all prose, headings hierarchy, data tables, inline citations (Author Year), footnote bodies, code blocks, equations.

CONVERT figure captions to plain paragraphs prefixed 'Caption:'.
Output ONLY the cleaned Markdown. No commentary. No preamble."""

PROMPT_PATH = "/THE_VAULT/prompts/notebooklm/best.txt"
HASH_LOG_PATH = "cleaned_hashes.txt"

def get_cleaning_prompt():
    if os.path.exists(PROMPT_PATH):
        with open(PROMPT_PATH, "r") as f:
            return f.read().strip()
    return DEFAULT_PROMPT

def get_file_hash(content: str) -> str:
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def load_cleaned_hashes(dir_path: str) -> set:
    hash_file = os.path.join(dir_path, HASH_LOG_PATH)
    if os.path.exists(hash_file):
        with open(hash_file, "r") as f:
            return set(line.strip() for line in f)
    return set()

def save_hash(dir_path: str, file_hash: str):
    hash_file = os.path.join(dir_path, HASH_LOG_PATH)
    with open(hash_file, "a") as f:
        f.write(f"{file_hash}\n")

def clean_chunk(text: str, prompt: str) -> str:
    try:
        response = ask(
            prompt=text,
            task='clean',
            privacy=Privacy.INTERNAL,
            system=prompt,
            stream=False
        )
        if hasattr(response, '__iter__') and not isinstance(response, str):
            return "".join(list(response))
        return response
    except Exception as e:
        print(f"Error: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(description="Clean markdown chunks for NotebookLM.")
    parser.add_argument("input", help="Path to .md file or chunks_manifest.json")
    args = parser.parse_args()
    
    input_path = os.path.abspath(args.input)
    input_dir = os.path.dirname(input_path)
    
    manifest = []
    if input_path.endswith(".json"):
        with open(input_path, "r") as f:
            manifest = json.load(f)
    else:
        # Run chunker first (simplified for this MVP)
        from tools import chunker
        # For real use, we'd call the CLI or use the library
        # Here we assume pre-chunked if manifest or we handle it if possible
        # For simplicity in this script, we'll focus on manifest processing
        print("Please provide a chunks_manifest.json")
        sys.exit(1)
        
    prompt = get_cleaning_prompt()
    cleaned_hashes = load_cleaned_hashes(input_dir)
    
    cleaned_content = []
    total = len(manifest)
    
    emit('cleaner', 'started', {'total_chunks': total})
    
    for i, entry in enumerate(manifest):
        chunk_file = entry['file']
        chunk_path = os.path.join(input_dir, chunk_file)
        
        with open(chunk_path, "r") as f:
            text = f.read()
            
        file_hash = get_file_hash(text)
        cached_clean_path = os.path.join(input_dir, f"clean_{chunk_file}")
        
        if file_hash in cleaned_hashes and os.path.exists(cached_clean_path):
            print(f"Skipping {chunk_file} (cached)")
            with open(cached_clean_path, "r") as f:
                cleaned_content.append(f.read())
        else:
            print(f"Cleaning chunk {i+1}/{total} ({(i+1)/total*100:.1f}%)...")
            try:
                clean_text = clean_chunk(text, prompt)
                cleaned_content.append(clean_text)
                
                with open(cached_clean_path, "w") as f:
                    f.write(clean_text)
                save_hash(input_dir, file_hash)
            except Exception as e:
                emit('cleaner', 'error', {'chunk': chunk_file, 'error': str(e)}, level='ERROR')
                sys.exit(1)
                
    output_name = os.path.basename(input_dir) + "_clean.md"
    output_path = os.path.join(os.path.dirname(input_dir), output_name)
    
    with open(output_path, "w") as f:
        f.write("\n\n".join(cleaned_content))
        
    emit('cleaner', 'completed', {'output': output_path})
    print(f"Reassembled into {output_path}")

if __name__ == "__main__":
    main()
