# Jarvis Coding Agent

The **Coding Agent** is the heart of Jarvis's intelligence. It is a multi-threaded Python HTTP server that bridges your local editor (Neovim) with powerful Large Language Models (LLMs) running via Ollama.

## Architecture

- **Path**: `services/coding_agent.py`
- **Runtime**: `/THE_VAULT/jarvis` (Production)
- **Port**: `7002`
- **Concurrency**: Uses `ThreadingHTTPServer` to handle multiple requests simultaneously (e.g., performing a code fix while allowing a cancellation request).

## Core Endpoints

### 1. `POST /chat`
- **Purpose**: General-purpose AI chat with project context.
- **Payload**: `{"prompt": "...", "context": "..."}`
- **Logic**: Routes to the `chat` model (typically Qwen3-14B). Uses RAG (Retrieval-Augmented Generation) if codebase indexing is available.

### 2. `POST /complete`
- **Purpose**: "Fill-In-the-Middle" (FIM) code completion.
- **Payload**: `{"prefix": "...", "suffix": "..."}`
- **Logic**: Optimized for low-latency using smaller models (e.g., Qwen2.5-Coder-1.7B).

### 3. `POST /fix`
- **Purpose**: Autonomous agentic loop to fix complex bugs or implement features.
- **Payload**: `{"task": "...", "file_path": "..."}`
- **Logic**: Invokes `pipelines/agent_loop.py`. This is a blocking call that can be terminated via `/cancel`.

### 4. `POST /research_manual`
- **Purpose**: Performs technical web research.
- **Payload**: `{"query": "..."}`
- **Logic**: Invokes the SearXNG-powered `pipelines/research_agent.py`. Returns the path to a summarized markdown report.

### 5. `POST /prefetch`
- **Purpose**: Performance optimization (Cold start elimination).
- **Payload**: `{"model_alias": "chat" | "complete"}`
- **Logic**: Triggers a minimal "warm-up" call to Ollama to ensure the model weights are loaded into GPU/VRAM before they are needed.

### 6. `POST /analyze_error`
- **Purpose**: Explains compilation/LSP errors at the cursor.
- **Logic**: Extracts diagnostic context and provides a concise fix suggestion.

### 7. `POST /summarize_git`
- **Purpose**: Generates semantic commit messages.
- **Logic**: Analyzes `git diff --cached` and produces a Conventional Commits-style message.

### 8. `POST /cancel`
- **Purpose**: Terminates an active long-running task (like `/fix`).

## Management

The coding agent is managed as a user-level Systemd service:

```bash
systemctl --user status jarvis-coding-agent.service
systemctl --user restart jarvis-coding-agent.service
```

Logs are stored in `/THE_VAULT/jarvis/logs/`.
