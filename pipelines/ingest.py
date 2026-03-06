import os
import argparse
import sys
import json
import shutil
from typing import Optional
from lib.event_bus import emit
from tools import chunker
from tools import cleaner
from lib import anythingllm_client

# /THE_VAULT/jarvis/pipelines/ingest.py

def run_pipeline(input_file: str, workspace_slug: str, once: bool = False):
    """
    Runs the full document ingestion pipeline:
    1. Chunking
    2. Cleaning (via AI)
    3. Uploading to AnythingLLM
    """
    input_file = os.path.abspath(input_file)
    if not os.path.exists(input_file):
        print(f"Error: File {input_file} not found.")
        sys.exit(1)
        
    base_dir = os.path.dirname(input_file)
    file_name = os.path.basename(input_file)
    chunks_dir = os.path.join(base_dir, "chunks_" + file_name.replace(".", "_"))
    
    emit('ingest', 'started', {'file': file_name, 'workspace': workspace_slug})
    print(f"Ingesting {file_name} into workspace '{workspace_slug}'...")

    # 1. Chunking
    try:
        print("Step 1/3: Chunking...")
        # We call the chunker logic
        with open(input_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        config = chunker.load_config()['chunker']
        chunks = chunker.chunk_by_heading(content, config['heading_levels'])
        
        # Filter min tokens
        min_tokens = config['min_chunk_tokens']
        chunks = [c for c in chunks if len(c['text']) / 4 >= min_tokens]
        
        os.makedirs(chunks_dir, exist_ok=True)
        manifest = []
        for i, chunk in enumerate(chunks):
            chunk_file = f"chunk_{i+1:04d}.md"
            chunk_path = os.path.join(chunks_dir, chunk_file)
            with open(chunk_path, "w", encoding="utf-8") as f:
                f.write(chunk['text'])
            manifest.append({'file': chunk_file, 'heading': chunk['heading']})
            
        manifest_path = os.path.join(chunks_dir, "chunks_manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
            
        emit('ingest', 'chunking_completed', {'chunks_count': len(chunks)})
    except Exception as e:
        emit('ingest', 'error', {'step': 'chunking', 'error': str(e)}, level='ERROR')
        raise

    # 2. Cleaning (AI-powered)
    try:
        print(f"Step 2/3: Cleaning {len(chunks)} chunks...")
        # Note: In a real scenario, we might want to run this in parallel
        # or handle partial failures. For MVP, we run sequentially.
        prompt = cleaner.get_cleaning_prompt()
        cleaned_hashes = cleaner.load_cleaned_hashes(chunks_dir)
        
        cleaned_files = []
        for i, entry in enumerate(manifest):
            chunk_file = entry['file']
            chunk_path = os.path.join(chunks_dir, chunk_file)
            with open(chunk_path, "r") as f:
                text = f.read()
            
            file_hash = cleaner.get_file_hash(text)
            clean_path = os.path.join(chunks_dir, f"clean_{chunk_file}")
            
            if file_hash in cleaned_hashes and os.path.exists(clean_path):
                cleaned_files.append(clean_path)
            else:
                print(f"  Cleaning chunk {i+1}/{len(chunks)}...")
                clean_text = cleaner.clean_chunk(text, prompt)
                with open(clean_path, "w") as f:
                    f.write(clean_text)
                cleaner.save_hash(chunks_dir, file_hash)
                cleaned_files.append(clean_path)
        
        emit('ingest', 'cleaning_completed', {'cleaned_count': len(cleaned_files)})
    except Exception as e:
        emit('ingest', 'error', {'step': 'cleaning', 'error': str(e)}, level='ERROR')
        raise

    # 3. Uploading to AnythingLLM
    try:
        print(f"Step 3/3: Uploading to AnythingLLM...")
        if not anythingllm_client.is_healthy():
            print("  Warning: AnythingLLM not reachable. Skipping upload.")
            emit('ingest', 'upload_skipped', {'reason': 'anythingllm_offline'})
        else:
            # For MVP, we upload each cleaned chunk as a separate document
            # or we could reassemble. The spec says "vector database ingestion".
            # reassembling for a unified "cleaned" doc might be better for AnythingLLM
            final_clean_path = os.path.join(base_dir, file_name.replace(".md", "_clean.md"))
            with open(final_clean_path, "w") as f_out:
                for cp in cleaned_files:
                    with open(cp, "r") as f_in:
                        f_out.write(f_in.read() + "\n\n")
            
            anythingllm_client.upload_document(workspace_slug, final_clean_path)
            emit('ingest', 'upload_completed', {'file': os.path.basename(final_clean_path)})
            print(f"  Successfully uploaded to {workspace_slug}")
    except Exception as e:
        emit('ingest', 'error', {'step': 'upload', 'error': str(e)}, level='ERROR')
        raise

    emit('ingest', 'completed', {'source': file_name})
    print(f"Done! Ingestion of {file_name} finished.")

def main():
    parser = argparse.ArgumentParser(description="Document Ingestion Pipeline")
    parser.add_argument("input", help="File to ingest")
    parser.add_argument("--workspace", default="jarvis_main", help="AnythingLLM workspace name")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    
    args = parser.parse_args()
    run_pipeline(args.input, args.workspace, args.once)

if __name__ == "__main__":
    main()
