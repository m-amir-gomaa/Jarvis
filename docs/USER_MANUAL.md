# Jarvis AI - User Manual

Welcome to Jarvis! This manual explains how the entire local AI ecosystem works on your NixOS machine.

## Architecture Overview
Jarvis consists of several local services running via `systemctl --user`. Since you have no dedicated GPU, everything runs efficiently on CPU using `Ollama`.
- **jarvis-coding-agent**: Provides HTTP endpoints (port 7002) for Neovim integrations.
- **jarvis-ingest**: Watches the `/THE_VAULT/jarvis/inbox` folder. Drop Markdown/PDFs here to add them to your knowledge base.
- **jarvis-health-monitor**: Generates warnings if CPU usage or RAM usages spike, pausing inference if necessary.
- **jarvis-git-monitor**: Summarizes git commits.

## Using the CLI
Jarvis has a natural language CLI. You can simply ask it what you want to do:
```bash
jarvis "open dashboard"
jarvis "check status"
jarvis "clean this pdf for notebooklm"
jarvis "pause" # Stops Ollama processes from eating CPU
```

## Neovim Integration
The Neovim plugin hooks into the `jarvis-coding-agent` via asynchronous requests (`plenary.curl`), which ensures that Neovim is never blocked when asking an LLM a question.

### Keybindings (mapped to `<leader>j`):
- `<leader>jc` — **Chat with RAG**: A prompt will appear. Your query is sent to Jarvis which searches your indexed codebase and answers it based on the current context.
- `<leader>jf` — **Fix Diagnostics**: Selects all current errors in the file, sends them with the current buffer context to the agent loop, and returns a unified diff.
- `<leader>je` — **Explain Code**: Highlight a block of code and press `<leader>je` to get a succinct explanation in a split window.
- `<leader>ji` — **Index Project**: Run this from the root of a project. Jarvis will recursively parse and embed your source code into `/THE_VAULT/jarvis/index/codebase.db`.
- `<leader>jt` — **Toggle FIM Suggestions**: Enables or disables background autocomplete suggestions.

## Indexing & RAG (Retrieval-Augmented Generation)

### How Indexing Works
When you type `<leader>ji` inside your project or drop a document into `/THE_VAULT/jarvis/inbox`, Jarvis converts the text into mathematical vectors (embeddings) using the `nomic-embed-text` model. These vectors are saved into a SQLite database (`nixosenv.db`, `codebase.db`, etc.).

### How RAG Works
When you ask a question via `<leader>jc`, Jarvis:
1. Turns your question into a vector.
2. Performs a "Hybrid Search" (Vector similarity + Keyword matching) in the database.
3. Takes the top 3 most relevant chunks of code/text.
4. Feeds those chunks to the `qwen3:14b` model alongside your question.

This ensures the AI knows about your *exact* codebase before answering, compensating for the fact that a 14B model doesn't have the vast knowledge of a 70B cloud model.

## Tuning & Optimization
- **Swap / Swappiness**: Your NixOS configuration relies on a 4GB swapfile and a swappiness of 10 (`boot.kernel.sysctl = { "vm.swappiness" = 10; }`). This ensures that background apps (like Firefox) are sent to swap, keeping precious RAM available for the 14B model weights.
- **Prompt Optimizer**: An automated `systemd` timer runs every Sunday to refine its internal prompts based on feedback. You can provide feedback using: `jarvis "thumbs-up"` or `jarvis "thumbs-down"` on the last operation.

## Troubleshooting
- **AI seems slow**: Run `jarvis status`. Check if the models are loaded into memory.
- **Neovim isn't responding or Jarvis commands fail**: The background server might have crashed. Restart it with: `systemctl --user restart jarvis-coding-agent`
- **Missing Knowledge**: If Jarvis says it doesn't know about a specific file, re-run `<leader>ji` to rebuild the codebase index.
