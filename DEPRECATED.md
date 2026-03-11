# This Project is Deprecated

**Deprecated:** March 2026
**Successor:** [NeoVex](https://github.com/m-amir-gomaa/NeoVex)
**Reason:** Architecture superseded — see README for full explanation.

This repository is kept as a reference and historical record of the ideas that carried forward into NeoVex. No new features, bug fixes, or maintenance will be performed.

## What Carried Forward Into NeoVex

The following concepts from Jarvis are being re-implemented in NeoVex from scratch, with better foundations:

- **External Reasoning System (ERS)** — ReAct-style multi-step agent loop, now built on `rig` + `agentai` in Rust instead of Python async chains
- **Hybrid Model Router** — cloud provider hierarchy with budget tracking and Ollama fallback, now cloud-first by default instead of local-first
- **RAG Pipeline** — codebase indexing and retrieval, now using cloud embedding APIs as the primary path with local fallback
- **MCP Integration** — Model Context Protocol for external data sources, now the dedicated data layer rather than a mixed-in feature
- **Neovim Bridge** — Lua/Rust plugin via `mlua`, replacing the Python LSP server approach
- **NixOS Integration** — declarative flake configuration, now designed from the start rather than bolted on

## What Was Left Behind

- The Python runtime entirely
- The local-first model priority
- The organic, unplanned architecture
- The capability-based security model (to be redesigned in NeoVex)

## How to Migrate

NeoVex is not yet ready for use. When it reaches a functional state, a migration guide will be published in the NeoVex repository.

In the meantime, Jarvis continues to run as-is. No breaking changes will be introduced, but no fixes will be applied either.
