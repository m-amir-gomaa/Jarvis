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
- Stored at `/THE_VAULT/jarvis/context/active_session_token` (Mode 600).
- LSP clients must provide this token to gain `ELEVATED` (Trust 2) status.

### Capability Gates
- **BASIC (Trust 1)**: Anonymous/unauthenticated. Auto-grants `model:local`, `chat:basic`, `ide:read`.
- **ELEVATED (Trust 2)**: Authenticated. Can request `ide:edit`, `vcs:read`.
- **ADMIN (Trust 3)**: CLI/Manual. Full control, including `vcs:write`, `sys:manage`.

### OOB Approval Flow
1. Client requests a capability (e.g., `ide:edit`).
2. Server raises `CapabilityPending` if not auto-allowed.
3. User runs `jarvis pending` to see requests.
4. User runs `jarvis approve <id>` to grant/deny.
5. Client long-polls `/security/pending` to receive the result.

## 3. Data & Storage

All databases are consolidated in the Vault:
- `/THE_VAULT/jarvis/databases/knowledge.db`: RAG knowledge base.
- `/THE_VAULT/jarvis/databases/security_audit.db`: Audit logs and pending grants.
- `/THE_VAULT/jarvis/databases/api_usage.db`: Budget and token tracking.
- `/THE_VAULT/jarvis/databases/sessions.db`: Persistent security grants.

## 4. Operational Commands

- `make test-all`: Run full validation suite (Security, ERS, Models, IDE).
- `make rust-build`: Rebuild the Dashboard TUI.
- `jarvis status`: Check health of all sub-services.
- `jarvis approve <id>` / `jarvis pending`: Manage security requests.

## 5. Development Status

- **Core Engine**: 95% complete. Robust security and model routing.
- **IDE Integration**: 90% complete. End-to-end Lua logic with `conn_id` isolation.
- **Dashboard TUI**: Functional baseline. Live DB integration for Security/ERS tabs pending.
- **CLI V2**: Future roadmap item (migrating CLI from v1 to v2 primitives).

---
*Last Updated: March 7, 2026*
