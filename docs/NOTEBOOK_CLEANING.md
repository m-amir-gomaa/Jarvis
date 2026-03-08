# NotebookLM Resource Cleaning

Jarvis provides a specialized workflow to prepare your documents for **NotebookLM**. Since NotebookLM is text-only and has specific context limits, Jarvis includes tools to chunk large documents and clean them of "non-prose" noise (images, headers, references, etc.).

## The Workflow

The process involves two main steps:
1.  **Chunking**: Splitting a large Markdown file into smaller, manageable pieces (e.g., by heading).
2.  **Cleaning**: Using an LLM to remove boilerplate, images, and other noise while preserving content.

### 1. Chunking documents

Use `tools/chunker.py` to split a large file. This creates a directory of chunks and a `chunks_manifest.json`.

```bash
# Split by headings (default)
python tools/chunker.py my_document.md

# Split by fixed tokens (approx 1500 tokens with 200 overlap)
python tools/chunker.py my_document.md --strategy tokens --max-tokens 1500 --overlap 200
```

- **Output Dir**: Defaults to `chunks/` next to your input file.
- **Manifest**: `chunks/chunks_manifest.json` tracks the order and metadata of chunks.

### 2. Cleaning for NotebookLM

Use `tools/cleaner.py` to process the chunks. This script uses an LLM to strip noise and reassemble the document.

```bash
python tools/cleaner.py chunks/chunks_manifest.json
```

#### What it does:
- **Removes**: Image tags, figure references, page numbers, headers/footers, index lists, and repeated copyright boilerplate.
- **Preserves**: Prose, headings, data tables, inline citations, code blocks, and equations.
- **Converts**: Figure captions become plain paragraphs prefixed with `Caption:`.
- **Caching**: Uses SHA256 hashes to skip cleaning for chunks that haven't changed.

### Final Reassembly
Once all chunks are cleaned, the script reassembles them into a single file named `[source_dir]_clean.md`.

## Configuration

### Chunker Configuration
Located in `config/chunker.toml`:
```toml
[chunker]
default_strategy = "heading"
max_tokens = 1500
overlap_tokens = 200
heading_levels = [2, 3] # Split by ## and ### headings
```

### Cleaner Prompt
The cleaning logic is driven by a system prompt. You can override the default by creating:
- `/THE_VAULT/prompts/notebooklm/best.txt`

The default prompt focuses on making the document "pure prose" for maximum NotebookLM semantic understanding.
