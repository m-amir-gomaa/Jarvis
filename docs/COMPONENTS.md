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

- `router.py`: `ModelRouter`. The central dispatcher for model aliases and provider-agnostic generation.
- `adapters/base.py`: Abstract Base Class for all model providers.
- `adapters/ollama.py`: Integration with local Ollama API. Standardized 600s timeout for stability.
- `adapters/anthropic.py`, `adapters/openai.py`, etc.: Adapters for external cloud providers.

## 4. Services & Entrypoints

- `jarvis.py`: The main CLI entrypoint. Orchestrates intent classification, service management, and high-level routing.
- `services/jarvis_lsp.py`: The Jarvis LSP and HTTP bridge server.
- `services/health_monitor.py`: Periodic background check for service and model availability.
- `bin/jarvis-monitor`: (Compiled Rust) The terminal dashboard.

## 5. Configuration & Data

- `config/models.toml`: Defines model aliases and fallback behaviors.
- `config/security.toml`: Configures trust floors and auto-grant policies.
- `/THE_VAULT/jarvis/databases/`: Persistent SQLite storage for events, knowledge, and security audits.
