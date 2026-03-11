# ⚠️ DEPRECATED — Jarvis: Personal AI Orchestrator (V3.5)

> **This project is no longer maintained.**
> Development has moved to [NeoVex](https://github.com/m-amir-gomaa/NeoVex), which supersedes Jarvis entirely.

---

## Why Jarvis is Deprecated

Jarvis solved a real problem — agentic AI orchestration inside Neovim on NixOS — but it hit the limits of its own foundations. It was built in Python, local-first by design, and grew organically over several iterations into something that worked but was increasingly hard to extend.

The core issues that led here:

**Python and the GIL.** Concurrent agent workstreams in Python mean fighting the Global Interpreter Lock. Async helps, but it doesn't solve the problem — it just moves it. A system designed around multi-agent parallelism needs a better substrate.

**Local-first was the wrong default.** Jarvis routed to local Ollama models first and treated cloud APIs as a fallback. That hierarchy is backwards for anyone who wants the best possible results. The best models are in the cloud. Local should be the fallback of last resort, not the default.

**Architecture grew ahead of design.** Jarvis was built iteratively, feature by feature, without a locked vision document. The result is a system that works but whose subsystems are loosely coupled in ways that weren't planned. NeoVex starts with the vision locked first.

Jarvis's ideas — the ERS, the RAG pipeline, the model router, the Neovim bridge, the MCP integration — all carry forward into NeoVex. The code does not.

---

## What Replaces It

**[NeoVex](https://github.com/m-amir-gomaa/NeoVex)** — a cloud-native AI orchestration layer for Neovim, built in Rust, optimized for NixOS.

| | Jarvis | NeoVex |
|---|---|---|
| Language | Python 3.12 | Rust |
| Model priority | Local-first (Ollama) | Cloud-first (Gemini, Claude, GPT-4) |
| Local fallback | Default path | Last resort only |
| Concurrency | asyncio + GIL | tokio + Rust ownership |
| Architecture | Grew organically | Vision-locked before code |
| Status | **Deprecated** | Active development |
| License | Apache 2.0 | GPL v3 |

If you are using Jarvis today, NeoVex is not yet ready to replace it — it is in early architecture phase. Watch the NeoVex repository for progress.

This repository is archived for reference. No further commits will be made to Jarvis.

---

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
## ⚖️ License
This project is licensed under the **Apache License 2.0**. See the [LICENSE](LICENSE) file for details.
