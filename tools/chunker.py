import os
import re
import json
import argparse
import tomllib
from typing import List, Dict, Optional

# /home/qwerty/NixOSenv/Jarvis/tools/chunker.py

DEFAULT_CONFIG = {
    'chunker': {
        'default_strategy': 'heading',
        'max_tokens': 1500,
        'overlap_tokens': 200,
        'min_chunk_tokens': 10,
        'heading_levels': [2, 3]
    }
}

def load_config():
    path = "/home/qwerty/NixOSenv/Jarvis/config/chunker.toml"
    if os.path.exists(path):
        with open(path, "rb") as f:
            return tomllib.load(f)
    return DEFAULT_CONFIG

def chunk_by_heading(content: str, levels: List[int]) -> List[Dict]:
    """Splits markdown by headings of specified levels."""
    # Ensure levels is a range string for the regex
    level_range = f"{min(levels)},{max(levels)}"
    pattern = r'^#{' + level_range + r'}\s+.+$'
    matches = list(re.finditer(pattern, content, re.MULTILINE))
    
    chunks = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i+1].start() if i + 1 < len(matches) else len(content)
        heading = match.group(0).strip('#').strip()
        text = content[start:end]
        
        chunks.append({
            'text': text,
            'char_start': start,
            'char_end': end,
            'heading': heading
        })
    
    # Handle content before first heading
    if matches and matches[0].start() > 0:
        chunks.insert(0, {
            'text': content[0:matches[0].start()],
            'char_start': 0,
            'char_end': matches[0].start(),
            'heading': 'Preamble'
        })
    elif not matches:
        chunks.append({
            'text': content,
            'char_start': 0,
            'char_end': len(content),
            'heading': 'Full Document'
        })
        
    return chunks

def chunk_by_tokens(content: str, max_tokens: int, overlap_tokens: int) -> List[Dict]:
    """Splits text into fixed-size token chunks (approx 4 chars per token)."""
    char_stride = (max_tokens - overlap_tokens) * 4
    char_size = max_tokens * 4
    
    chunks = []
    for i in range(0, len(content), char_stride):
        start = i
        end = min(i + char_size, len(content))
        text = content[start:end]
        
        chunks.append({
            'text': text,
            'char_start': start,
            'char_end': end,
            'heading': f'Chunk {len(chunks)+1}'
        })
        if end == len(content):
            break
            
    return chunks

def chunk_by_page(content: str) -> List[Dict]:
    """Splits by horizontal rules (---) or form-feed (\f)."""
    parts = re.split(r'(\n---\n|\f)', content)
    chunks = []
    curr_pos = 0
    
    for i, part in enumerate(parts):
        if part in ('\n---\n', '\f'):
            curr_pos += len(part)
            continue
            
        chunks.append({
            'text': part,
            'char_start': curr_pos,
            'char_end': curr_pos + len(part),
            'heading': f'Page {len(chunks)+1}'
        })
        curr_pos += len(part)
        
    return chunks

def main():
    parser = argparse.ArgumentParser(description="Chunk markdown files for RAG.")
    parser.add_argument("input", help="Path to .md file")
    parser.add_argument("--strategy", choices=['heading', 'tokens', 'page'], default=None)
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--overlap", type=int, default=None)
    parser.add_argument("--out-dir", help="Output directory")
    
    args = parser.parse_args()
    config = load_config()['chunker']
    
    strategy = args.strategy or config['default_strategy']
    max_tokens = args.max_tokens or config['max_tokens']
    overlap = args.overlap or config['overlap_tokens']
    
    with open(args.input, "r", encoding="utf-8") as f:
        content = f.read()
        
    if strategy == 'heading':
        chunks = chunk_by_heading(content, config['heading_levels'])
    elif strategy == 'tokens':
        chunks = chunk_by_tokens(content, max_tokens, overlap)
    elif strategy == 'page':
        chunks = chunk_by_page(content)
        
    # Filter min tokens
    min_tokens = config['min_chunk_tokens']
    chunks = [c for c in chunks if len(c['text']) / 4 >= min_tokens]
    
    out_dir = args.out_dir or os.path.join(os.path.dirname(args.input), "chunks")
    os.makedirs(out_dir, exist_ok=True)
    
    manifest = []
    for i, chunk in enumerate(chunks):
        chunk_file = f"chunk_{i+1:04d}.md"
        chunk_path = os.path.join(out_dir, chunk_file)
        
        with open(chunk_path, "w", encoding="utf-8") as f:
            f.write(chunk['text'])
            
        manifest.append({
            'chunk_id': i + 1,
            'file': chunk_file,
            'char_start': chunk['char_start'],
            'char_end': chunk['char_end'],
            'heading': chunk['heading'],
            'token_estimate': len(chunk['text']) // 4
        })
        
    manifest_path = os.path.join(out_dir, "chunks_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        
    print(f"Split into {len(chunks)} chunks, total {len(content)} chars")

if __name__ == "__main__":
    main()
