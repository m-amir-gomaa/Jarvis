# Jarvis Component Reference (V3)

This document provides a technical audit of the core Jarvis implementation files, organized by subsystem.

## 1. Security Subsystem (`lib/security/`)

- `context.py`: Defines `TrustLevel`, `CapabilityGrant`, and `SecurityContext`. Handles the recursive `has()` and `require()` logic.
- `grants.py`: Contains `CapabilityGrantManager` and `CapabilityRequest`. Implements the logic for interactive and OOB approvals.
- `audit.py`: `AuditLogger` implementation. Manages the `security_audit.db` schema and write operations.
- `store.py`: `GrantStore` for serializing and restoring persistent capability grants.
- `exceptions.py`: Custom security exceptions (`CapabilityDenied`, `CapabilityPending`, `TrustLevelError`).
- `secrets.py`: `SecretsManager` for handling AES-256 encrypted API keys in the Vault.

## 2. Reasoning Subsystem (`lib/ers/`)

- `chain.py`: `ChainLoader` for loading and validating YAML-based `ReasoningChain` definitions.
- `augmentor.py`: `ChainAugmentor`. The core execution engine for ERS steps, including batch parallelism and RAM gating.
- `schema.py`: Pydantic models for ERS types (`ReasoningStep`, `ERSExecutionResult`).
- `access_protocol.py`: Defines how ERS steps interact with the `SecurityContext`.
- `seed_loader.py`: `PromptSeedLoader`. Wraps legacy prompts into modern ERS envelopes.

## 3. Model & LLM Subsystem (`lib/models/`)

- `router.py`: `ModelRouter`. The central dispatcher for model- [lib/model_router.py](file:///home/qwerty/NixOSenv/Jarvis/lib/model_router.py): Policy layer for local vs cloud routing.
- [lib/prefs_manager.py](file:///home/qwerty/NixOSenv/Jarvis/lib/prefs_manager.py): Persistent user-defined preference overrides.
- [lib/ollama_client.py](file:///home/qwerty/NixOSenv/Jarvis/lib/ollama_client.py): Core bridge to the local inference engine.
 Standardized 600s timeout for stability.
- `adapters/anthropic.py`, `adapters/openai.py`, etc.: Adapters for external cloud providers.

## 4. Services & Entrypoints

- `services/coding_agent.py`: The core coding assistant service. Provides endpoints for FIM completion, RAG chat, SSE streaming, error analysis, and model prefetching.
- `bin/jarvis-monitor`: (Compiled Rust) The terminal dashboard.

## 5. Neovim Integration (`lua/jarvis/`)

- `agent.lua`: Core interface for Jarvis commands (`/fix`, `/explain`, `/index`, etc.). Implements floating window UX and Tree-sitter context extraction.
- `chat.lua`: Streaming chat implementation using Server-Sent Events (SSE).
- `dap.lua`: Debug Adapter Protocol configuration for Rust and Python, featuring automated exception analysis.
- `init.lua`: Plugin entrypoint and configuration defaults.

## 6. Configuration & Data

- `config/models.toml`: Defines model aliases and fallback behaviors.
- `config/security.toml`: Configures trust floors and auto-grant policies.
- `/THE_VAULT/jarvis/databases/`: Persistent SQLite storage for events, knowledge, and security audits.
