# Jarvis: Personal AI Orchestrator (V3)

Jarvis is a heavy-duty, local-first AI orchestration layer designed for developers on NixOS. It provides a principled, capability-based security model and an External Reasoning System (ERS) for complex, multi-step tasks.

## 🚀 Quick Links
- **[Installation](docs/INSTALL.md)**: Setup, models, and vault configuration.
- **[Usage Guide](docs/USAGE.md)**: Master the CLI, Neovim actions, and Dashboard TUI.
- **[Architecture](docs/ARCHITECTURE.md)**: Deep dive into the security and reasoning engines.
- **[Component Reference](docs/COMPONENTS.md)**: File-by-file technical audit.
- **[API Key Guide](docs/API_KEYS.md)**: Obtaining and securing external model keys.
- **[Developer Guide](docs/DEVELOPER_GUIDE.md)**: Contribution and AI engineering resources.
- **[AI Terminology](docs/AI_TERMINOLOGY.md)**: Foundational concepts for non-AI devs.
- **[Creative Uses](docs/CREATIVE_USES.md)**: System automation & coding excellence.
- **[Documentation Guide](docs/READING_GUIDE.md)**: How to navigate these resources.
- **[Knowledge Base & RAG](docs/KNOWLEDGE_BASE.md)**: Deep technicals on indexing and retrieval.
- **[Model Comparison](docs/MODELS_OVERVIEW.md)**: Local vs. Cloud (Technical deep-dive).
- **[Porting & Decoupling](docs/PORTING_GUIDE.md)**: Windows, other distros, and IDE agnosticism.

## 🏛️ Core Principles

1. **Local-First**: 100% functional without an internet connection using Ollama-hosted models.
2. **Strict Security**: Capability-based access control (CBAC). Every file read, shell execution, or network call is gated and audited.
3. **Low-Latency IDE Bridge**: Dedicated LSP server for Neovim with non-blocking async intelligence.
4. **Persistent Reasoning**: Multi-step ERS chains for tasks like deep research, git summarization, and NixOS verification.

## 🛠️ Tech Stack
- **Backend**: Python 3.12 (Asynchronous, Pydantic, Jinja2).
- **IDE**: Neovim + Lua (Custom LSP client).
- **Dashboard**: Rust + Ratatui (Terminal UI).
- **Models**: Ollama (Qwen3-14B primary, Qwen3-8B chat, Qwen2.5-Coder primary).
- **Storage**: SQLite + `/THE_VAULT/` (HDD optimized).

## 📊 Maintenance
- Run `make test-all` to verify security and model health.
- Run `make backup` or `make archive` to protect your vault data.
- See **[docs/BACKUP.md](docs/BACKUP.md)** for details.

---
*Powered by the m-amir-gomaa/Jarvis V3 stack.*