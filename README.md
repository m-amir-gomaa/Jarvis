# Jarvis: Personal AI Orchestrator (V3.5)

Jarvis is a heavy-duty, local-first AI orchestration layer designed for developers on NixOS. It provides a principled, capability-based security model and an External Reasoning System (ERS) for complex, multi-step tasks.

## 🧠 Agentic Intel (v3.5)
The **Agentic Intel** upgrade introduces three core pillars of intelligence:
- **External Reasoning System (ERS)**: Multi-step async chains with dynamic rerouting and LLM-driven self-correction.
- **Hybrid RAG Pipeline**: FAISS-powered semantic search across localized codebases.
- **Hybrid Model Router**: Intelligent routing between local (Ollama) and cloud models with cost-aware fallback.

## 🚀 Documentation (Phase 1: Subsystems)
- **[ERS Internals](docs/internals/ers.md)**: Chain of thought & validation logic.
- **[RAG & Indexing](docs/internals/rag.md)**: FAISS, Embeddings, and background indexing.
- **[Model Router](docs/internals/router.md)**: Alias system and prefetching.

## ⌨️ Documentation (Phase 2: Usage)
- **[Neovim Plugin Master Guide](docs/usage/neovim.md)**: Every command and IDE feature.
- **[CLI Reference](docs/usage/cli.md)**: Service management and knowledge queries.
- **[NixOS Deployment](docs/deployment/nixos.md)**: Systemd units and flake integration.

## 🚀 Legacy Quick Links
- **[Installation](docs/INSTALL.md)**: Setup, models, and vault configuration.
- **[Interaction Interfaces](docs/INTERFACES.md)**: Every way to talk to Jarvis (CLI, IDE, TUI, Voice).
- **[Architecture](docs/ARCHITECTURE.md)**: Deep dive into the security and reasoning engines.

## 🏛️ Core Principles

1. **Local-First**: 100% functional without an internet connection using Ollama-hosted models.
2. **Strict Security**: Capability-based access control (CBAC). Every file read, shell execution, or network call is gated and audited.
3. **Low-Latency IDE Bridge**: Dedicated LSP server for Neovim with non-blocking async intelligence.
4. **Knowledge Synergy**: Continuous background indexing (via `jarvis-indexer`) keeps your local RAG engine synchronized with your codebases.

## 🛠️ Tech Stack
- **Backend**: Python 3.12 (Asynchronous, Pydantic).
- **IDE**: Neovim + Lua (Custom LSP client via Plenary).
- **Search**: FAISS + nomic-embed-text.
- **Deployment**: NixOS Flakes + Systemd user services.

---
*Powered by the m-amir-gomaa/Jarvis V3 stack.*