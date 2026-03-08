# Jarvis Man Page

**NAME**
`jarvis` - Local-First AI Orchestrator with Strict Security and ERS

**SYNOPSIS**
`jarvis [OPTIONS] [COMMAND]`
`jarvis 'NATURAL LANGUAGE PROMPT'`

**DESCRIPTION**
`jarvis` is a heavy-duty local-first AI orchestrator designed for NixOS. It implements a principled, **Capability-Based Access Control (CBAC)** security model (Trust Levels 0-4) and an **External Reasoning System (ERS)** for multi-step tasks. Since V3, **Shadow Mode** is disabled; every sensitive action (filesystem, network, subprocess) is strictly gated and requires explicit user approval unless auto-granted.

**KEY ARCHITECTURAL COMPONENTS**
- **Security Manager**: The core gatekeeper. Enforces trust ceilings and handles interactive/OOB approvals. Tracks session identification via tokens stored in the Vault.
- **ERS (External Reasoning System)**: Executes complex workloads via YAML-defined chains. Each step runs in an isolated child security context with auto-revocation of temporary grants.
- **Model Hub**: A unified router for local (Ollama) and cloud models. Standardized 600s timeouts ensure stability for CPU-bound inference.
- **Antigravity IDE Layer**: Custom LSP bridge for Neovim providing asynchronous code actions (Explain, Fix, Refactor) with session-level isolation.

**COMMANDS**
- `status`: Displays the health of all Jarvis background services (systemd), Ollama load status, current budget, and session authentication status.
- `start / stop`: Starts or stops all background services (Ingest, Health, Coding Agent).
- `pause / resume`: Suspends or continues AI inference by sending SIGSTOP/SIGCONT to the Ollama process.
- `uptime`: Shows how long each background service has been running.
- `pending`: Lists all active out-of-band (OOB) capability requests from IDE or remote sessions.
- `approve <ID>`: Grants a pending capability request. Use `deny <ID>` to reject.
- `cap [list|grant|revoke] <CAP>`: Granular capability management. `grant` adds a persistent permission; `revoke` removes it.
- `associate [CATEGORY | list | remove CATEGORY]`: Links the current directory to a knowledge category for context-aware RAG.
- `config [set|get|list|reset] [KEY] [VAL]`: Manage user preferences (e.g., `models.default_local`). `reset` restores factory defaults.
- `set-key <PROVIDER> <KEY>`: Securely stores an encrypted API key in the Vault. Supported: `anthropic`, `openai`, `google`, `deepseek`, `groq`, `openrouter`.
- `keys`: List and verify the status of all configured API keys.
- `index [OPTIONS]`: Indexes the current codebase for the coding agent. Supports `--category` and `--privacy` [0-3] flags.
- `ingest <URL/FILE>`: Indexes documents into the RAG knowledge base.
- `learn [TOPIC | URL]`: Assisted language learning or direct ingestion with metadata.
- `query "<QUESTION>"`: Performs a RAG search against the Vault databases. Automatically uses associations from the current directory.
- `dashboard`: Launches the Rust TUI monitor.
- `backup / archive`: Creates backups or compressed archives of the Jarvis codebase and Vault.

**ERS INTENTS**
- `'research ...'`: Triggers `research_deep.yaml` for extensive web and local analysis.
- `'summarize git ...'`: Triggers `git_summarize.yaml` to generate human-readable changelogs.
- `'validate nixos ...'`: Triggers `nixos_verify.yaml` to check configuration sanity using local models.

**ENVIRONMENT**
- `JARVIS_ROOT`: Override the default project directory.
- `VAULT_ROOT`: Override the secure data storage root (Default: `/THE_VAULT/jarvis`).

**FILES**
- `/THE_VAULT/jarvis/databases/security_audit.db`: Central audit trail and pending grant storage.
- `/THE_VAULT/jarvis/databases/knowledge.db`: RAG knowledge base and embeddings.
- `/THE_VAULT/jarvis/context/active_session_token`: The source of truth for session authentication.

**SECURITY PROTOCOL**
Capabilities (e.g., `file_read`, `shell_exec`) are requested dynamically. If not auto-granted by a trust level:
1. The process raises `CapabilityPending`.
2. The user is notified via CLI (Interactive) or long-polling (OOB).
3. The task pauses until `jarvis approve` is executed.

**SEE ALSO**
`ollama(1)`, `nix(1)`

**AUTHOR**
Created by Antigravity AI for the Jarvis Project.
