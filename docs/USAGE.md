# Jarvis Usage Guide (V3)

Jarvis is designed for a multi-interface workflow: CLI for management, Neovim for coding, and TUI for monitoring.

## 1. CLI Usage (`jarvis.py`)

The CLI is the primary orchestration point. Before using it, ensure you have followed the **[Installation Guide](INSTALL.md)** and configured your **[API Keys](API_KEYS.md)**. For inspiration on what you can achieve, check out **[Creative Uses](CREATIVE_USES.md)**.

### Management Commands
- `jarvis start [alias]`: Initialize all or specific systemd services.
- `jarvis stop [alias]`: Terminate services gracefully.
- `jarvis restart [alias]`: Restart a specific service.
- `jarvis status [alias]`: Health check (**[Ollama](SYSTEM_TWEAKS.md)**, services, budget, RAG status).
- `jarvis uptime [alias]`: Show how long a service has been active.
- `jarvis models [list|active|select]`: Manage AI models and aliases.
- `jarvis man`: View the technical **[Man Page](jarvis.1)**.

> [!TIP]
> For a deep dive into service aliases and automated watchdog features, see the **[Service Management Guide](SERVICE_MANAGEMENT.md)**. For model selection and privacy-aware routing, see the **[Model Management Guide](MODEL_MANAGEMENT.md)**.

### Intelligence Commands
- `jarvis 'research [topic]'`: Triggers the ERS `research_deep` chain.
- `jarvis 'summarize my git commits'`: Triggers the ERS `git_summarize` chain.
- `jarvis 'validate my nixos config'`: Triggers the ERS `nixos_verify` chain.
- `jarvis index --category [cat] --privacy [level]`: Index codebase with metadata.
- `jarvis ingest [file]`: Index a document into semantic memory.
- `jarvis associate [category]`: Link current directory to a knowledge category.
- `jarvis associate list`: View active directory associations.

### 4. NotebookLM Preparation
- `python tools/chunker.py [file]`: Split documents for context management.
- `python tools/cleaner.py [manifest]`: Strip noise and prep for NotebookLM.

> [!TIP]
> For the full NotebookLM preparation workflow, see the **[NotebookLM Cleaning Guide](NOTEBOOK_CLEANING.md)**.

### Security & Permissions
- `jarvis pending`: View out-of-band capability requests.
- `jarvis approve [id]`: Grant or deny a pending request.
- `jarvis cap list`: View all active session and persistent grants.
- `jarvis cap grant <cap>`: Manually add a persistent permission.
- `jarvis cap revoke <cap>`: Remove a persistent permission.

### Configuration & Preferences
- `jarvis config set <key> <val> [--session]`: Override defaults (e.g., `models.default_local`).
- `jarvis config get <key>`: View current setting value.
- `jarvis config list`: Show all active user preferences.
- `jarvis config reset`: Restore factory sensible defaults.

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
