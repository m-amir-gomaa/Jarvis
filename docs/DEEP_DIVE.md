# 🕳️ Jarvis Technical Deep Dive

This document provides a low-level technical audit of the Jarvis system internals. It is intended for developers and security auditors who need to understand exactly how the machine thinks and protects itself.

---

## 🛡️ 1. Security Architecture: Capability-Based Access Control (CBAC)

Jarvis does not use traditional "Permissions" (user-based). Instead, it uses **Capabilities** (action-based).

### The Capability Grant Manager (`lib/security/grants.py`)
At the heart of the security system is the `CapabilityGrantManager`. It manages the lifecycle of a **Permission**:
1.  **Request**: An agent (CLI, LSP, or ERS step) requests a capability (e.g., `file_read: {path}`).
2.  **Ceiling Check**: The manager checks the `trust_ceiling` of the current `SecurityContext`. If the request exceeds the ceiling, it's denied instantly.
3.  **Resolution Logic**:
    *   **Persistent Grants**: Checked against `security_audit.db`.
    *   **Recursive Check**: If the current context has a parent (e.g., an ERS step inside a CLI session), the manager recursively checks the parent's grants.
    *   **Automatic Grants**: Trust Level 4 (Admin) and Trust Level 3 (User-Interactive) have pre-defined auto-grant lists for low-risk actions.
4.  **Suspension**: If no grant is found, the calling process raises `CapabilityPending`. This causes the thread to pause (or the ERS chain to block) until a user executes `jarvis approve <ID>`.

### Trust Levels
| Level | Name | Description | Ceiling |
| :--- | :--- | :--- | :--- |
| **0** | **Untrusted** | Default for remote, unauthenticated probes. | No capabilities. |
| **1** | **Sandbox** | Restricted ERS steps or "Shadow Mode" residue. | Read-only index. |
| **2** | **Elevated** | Standard Neovim/LSP session. | Selective disk/net. |
| **3** | **Interactive** | CLI user session. | High (File + Shell). |
| **4** | **Admin** | System recovery / Root tasks. | Absolute control. |

---

## 🧠 2. External Reasoning System (ERS)

ERS is what allows Jarvis to perform multi-step tasks that are too complex for a single LLM "Ask".

### The Chain Lifecycle (`lib/ers/chain.py`)
A "Chain" is a sequence of steps defined in YAML (e.g., `research_deep.yaml`).
- **Contextual Isolation**: Each step executes in its own `SecurityContext`. A step can be granted a capability that expires as soon as the step completes.
- **The Augmentor (`lib/ers/augmentor.py`)**: This component "augments" the prompt for each step using state from previous steps. It uses **Jinja2** templates to inject output variables (e.g., `{{ step1_result }}`).
- **Retry & Recovery**: Steps support `on_failure: continue | retry | stop` semantics.

### Intent Classification
Natural language is routed via `classify_intent` (a small, fast LLM call) into ERS chains.
- **System Roles**: Chains can specify `role: coding | research | system`. This determines which system prompt and model temperature is used.

---

## 🔍 3. Knowledge Base & RAG Implementation

Jarvis uses a high-performance, local-first RAG pipeline.

### Vector Storage (`lib/semantic_memory.py`)
- **Engine**: SQLite with the `sqlite-vec` extension for native vector search.
- **Embedding Generation**: Performed locally via `OllamaAdapter` using the `nomic-embed-text` model.
- **Search Logic**: Uses a two-stage approach. 
    1. **KNN Search**: Retrieves top `k` candidates via cosine similarity.
    2. **Metadata Filtering**: Results are filtered by `layer` (1: Core, 2: Docs, 3: Theory) and `category`.

### Codebase Association (`lib/knowledge_manager.py`)
Associations are stored in a dedicated table `codebase_associations`.
- **Recursive Directory Walk**: When you run a query, Jarvis walks up the directory tree from the CWD to find all associated resource categories. 
- **SQL Injection**: These categories are injected into the `WHERE m.category IN (...)` clause of the vector search, ensuring context is project-specific.

---

## 🔌 4. Antigravity IDE Layer (LSP Bridge)

The Neovim integration works via a custom LSP implementation (`jarvis_lsp.py`) and a sidecar HTTP server.

### Session Synchronization
- **Conn ID**: Every Neovim instance generates a unique `conn_id`.
- **Auth Tokens**: Authentication happens once via CLI (`jarvis authenticate`). The token is stored in `/THE_VAULT/jarvis/context/active_session_token`.
- **Sidecar**: A lightweight Flask server exposes endpoints for the Lua plugin to request capabilities without blocking the main LSP thread.

---

## 📡 5. Model Routing & Stability

The `ModelRouter` (`lib/model_router.py`) handles the "Brain" of the system.

### Inference Stability
- **Ollama Persistence**: Jarvis manages the Ollama state via `SIGSTOP`/`SIGCONT` (pause/resume commands) to free up CPU/GPU cycles instantly.
- **600s Timeouts**: All local inference calls have a strict 600-second timeout. This accounts for the shared CPU resources on standard laptop hardware (like the user's i7-1165G7).
- **Graceful Fallback**: If a local model fails or hits a budget limit, the router can pivot to cloud models (Anthropic, DeepSeek, etc.) if configured in `user_prefs.toml`.

---

## 📊 6. The Vault Partitioning
The Vault (`/THE_VAULT/jarvis/`) is logically partitioned for reliability:
- `/databases/`: SQLite files (Knowledge, Security, Budget, Inbox).
- `/context/`: Ephemeral session tokens and active ERS state.
- `/logs/`: Per-agent audit logs (Security, Execution).
- `/secrets/`: AES-256 encrypted API keys.

---

*This document is the living source of truth for the Jarvis V3 internals.*
