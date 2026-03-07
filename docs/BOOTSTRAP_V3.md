# Jarvis V3 Definitive Bootstrap

This document serves as the definitive source of truth for the Jarvis AI Orchestrator's state as of March 2026, following the V3 remediation and consolidation.

## 1. System Architecture Overview

Jarvis is a multi-modal AI orchestrator designed for local-first execution with secure external fallbacks.

- **CLI (`jarvis.py`)**: Entry point for management, session initialization, and OOB approvals.
- **LSP Service (`services/jarvis_lsp.py`)**: IDE bridge providing AI features (Explain, Fix, Refactor) to Neovim.
- **Security Engine (`lib/security/`)**: Capability-based access control with persistent grant storage and audit logging.
- **ERS (`lib/ers/`)**: Chained reasoning system for complex tasks (Research, Code Review).
- **Model Router (`lib/models/`)**: Unified interface for local (Ollama) and cloud (Anthropic, OpenAI, etc.) models.
- **The Vault**: Persistent storage for databases and secrets at `/THE_VAULT/jarvis/`.

## 2. Critical Security Protocols

### Session Management
- Tokens are generated on every CLI run: `_ensure_session_token()`.
- **Absolute Source of Truth**: `/THE_VAULT/jarvis/context/active_session_token` (Mode 600). 
- *Note:* Both the CLI and `jarvis_lsp.py` must synchronize on this path.

### Capability Gates
- **STRICT ENFORCEMENT**: Shadow Mode is **DISABLED**. Denied capabilities or insufficient trust levels will block execution and prompt the user (Interactive) or raise `CapabilityPending` (OOB).
- **BASIC (Trust 1)**: Anonymous/unauthenticated. Auto-grants `model:local`, `chat:basic`, `ide:read`.
- **ELEVATED (Trust 2)**: Authenticated. Can request `ide:edit`, `vcs:read`.
- **ADMIN (Trust 3)**: CLI/Manual. Full control, including `vcs:write`, `sys:manage`, and direct subprocess execution.

### OOB Approval Flow
1. Client requests a capability (e.g., `ide:edit`).
2. Server raises `CapabilityPending` if not auto-allowed.
3. User runs `jarvis approve <id>` to grant/deny.
4. Client long-polls `/security/pending?conn_id=...` to receive the result.

## 3. Data & Storage

All databases are consolidated in the Vault:
- `/THE_VAULT/jarvis/databases/knowledge.db`: RAG knowledge base.
- `/THE_VAULT/jarvis/databases/security_audit.db`: Audit logs and pending grants.
- `/THE_VAULT/jarvis/databases/api_usage.db`: Budget and token tracking.
- `/THE_VAULT/jarvis/databases/sessions.db`: Persistent security grants.

## 4. Operational Commands

- `make test-all`: Run full validation suite (Security, ERS, Models, IDE).
- `make rust-build`: Rebuild the Dashboard TUI (requires `ollama stop` to free RAM).
- `jarvis status`: Check health of all services, including budget and Ollama latency.
- `jarvis approve <id>` / `jarvis pending`: Manage security requests.

## 6. Documentation Ecosystem

Jarvis documentation is rebuilt from the ground up for V3 to ensure clarity and maintainability.

### Persistent Lifecycle
- **Source of Truth**: `docs/BOOTSTRAP_V3.md` must be updated after any major architectural change.
- **Redundancy Purge**: All V1/V2 legacy docs have been removed. Do NOT create independent `.md` files without linking them to the core suite.
- **Structure**:
    - `README.md` (Root): High-level overview and quick start.
    - `docs/INSTALL.md`: Comprehensive setup guide.
    - `docs/USAGE.md`: Interaction patterns (CLI/IDE/TUI).
    - `docs/ARCHITECTURE.md`: Subsystems, security flow, and Mermaid diagrams.
    - `docs/COMPONENTS.md`: Technical reference for all `lib/` and `services/` modules.
    - `docs/DEVELOPER_GUIDE.md`: Contribution path, tutorials, and AI engineering resources.

### External Resources for AI Engineering
- **Youtube**: Andrej Karpathy's "Zero to Hero" series, Umar Jamil (Paper implementations).
- **Books**: "Hands-On Machine Learning with Scikit-Learn, Keras, and TensorFlow" (Geron), "Deep Learning" (Goodfellow).
- **Websites**: Hugging Face Course, Anthropic/OpenAI documentation, LangChain/LlamaIndex docs.

---
*Last Updated: March 8, 2026*
