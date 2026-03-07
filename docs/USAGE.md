# Jarvis Usage Guide (V3)

Jarvis is designed for a multi-interface workflow: CLI for management, Neovim for coding, and TUI for monitoring.

## 1. CLI Usage (`jarvis.py`)

The CLI is the primary orchestration point.

### Management Commands
- `jarvis start`: Initialize all systemd services.
- `jarvis stop`: Terminate all services gracefully.
- `jarvis status`: Health check (Ollama, services, budget, RAG status).
- `jarvis pause / resume`: Suspend/continue Ollama CPU inference (SIGSTOP/SIGCONT).

### Intelligence Commands
- `jarvis 'research [topic]'`: Triggers the ERS `research_deep` chain.
- `jarvis 'summarize my git commits'`: Triggers the ERS `git_summarize` chain.
- `jarvis 'validate my nixos config'`: Triggers the ERS `nixos_verify` chain.
- `jarvis ingest [file]`: Index a document into semantic memory.

### Security Interaction
- `jarvis pending`: View out-of-band capability requests.
- `jarvis approve [id]`: Grant or deny a pending request.

## 2. Neovim IDE Integration

Jarvis provides a suite of asynchronous AI actions in Neovim.

### Core Shortcuts (LazyVim Style)
- `<leader>ji`: Initialize Jarvis LSP and authenticate session.
- `<leader>je`: Explain current code selection (Diagnostic Lens).
- `<leader>jr`: Refactor current selection (least privilege edit).
- `<leader>jf`: Fix error at cursor.
- `<leader>jc`: Open Jarvis Chat in a sidebar.

### Inline Completion
Jarvis provides ghost-text completions using the `qwen3:1.7b` model.
- `Tab`: Accept completion.
- `Ctrl-]`: Manually trigger completion.

## 3. Dashboard TUI (`jarvis-monitor`)

The Rust-based monitoring tool provides real-time insights.

- **Dashboard Tab**: General health, latest LLM responses, and system events.
- **Security Tab**: Live audit trail and pending grant list.
- **ERS Tab**: Active reasoning chain progress and step outputs.
- **IDE Tab**: Neovim session status and connection health.

Launch via `jarvis dashboard`.
