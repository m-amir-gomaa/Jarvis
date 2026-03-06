# 🤖 Jarvis: Local AI Orchestrator for NixOS or any Linux distro with the Nix package manager 

[![NixOS](https://img.shields.io/badge/NixOS-25.11-blue.svg?logo=nixos&logoColor=white)](https://nixos.org)
[![Licence](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Jarvis** is a powerful, local-first AI coding assistant and system automation suite designed specifically for **NixOS**. It orchestrates multiple LLMs (Qwen3, Mistral) via Ollama to provide high-accuracy coding, research, and knowledge management—all running on your local CPU.

---

## 🏗️ Architecture: Repo vs. Vault

Jarvis is designed for high performance on limited hardware (i7-1165G7). To achieve this, it uses a unique dual-directory structure:

- **The Repository (`~/NixOSenv/Jarvis`)**: This is the source code repo you are looking at. It contains the logic, Neovim configuration, and NixOS modules. Code changes and Git operations happen here.
- **The Vault (`/THE_VAULT/jarvis`)**: This is the high-capacity runtime directory (located on a 744GB HDD). It stores the heavy lifting: Python virtual environments, LLM context, SQLite databases (`events.db`, `knowledge.db`), and indexed codebases.

---

## ✨ Key Features

- **3nd-Layer Knowledge Architecture**: Optimized- [x] **RAM-Aware Prefetching**: Predictively loads AI models into RAM based on your activity (Stage 2).
- [x] **Self-Heal Daemon**: Monitors and auto-restarts failed Jarvis services (Stage 3).
- [x] **Auto-Doc Syncer**: Automatically keeps documentation in sync with code changes (Stage 3).
- **Specialized Config Modes**: Dedicated `jarvis config nvim` and `jarvis config nixos` workflows for expert system management.
- **Safety & Personalization**: High-risk operation confirmations and long-term user profile memory.
- **TUI Dashboard**: High-performance Rust dashboard (`jarvis-monitor`) for real-time monitoring and **precise task labeling**.
- **Performance Metrics**: Every response now includes a **duration timestamp** (e.g., "Response took 1.45s") for performance tracking.

## Detailed Documentation

For deep dives into specific components, see:
- 🧩 **[Neovim Plugin](docs/NEOVIM_PLUGIN.md)**: Logic, commands, and UI.
- ⚙️ **[Coding Agent](docs/CODING_AGENT.md)**: Backend architecture and API.
- 🗺️ **[Optimization Roadmap](docs/OPTIMIZATION_ROADMAP.md)**: Project history and future stages.

---

## 🚀 Quick Start

### 1. Installation
Detailed instructions for NixOS, traditional Linux (with Nix), and manual setups are in:
👉 **[INSTALL.md](./INSTALL.md)**

### 2. Basic Usage
Once installed, use the unified CLI:
```bash
# Check service status
jarvis status

# Start background daemons
jarvis start

# Natural language tasking
jarvis "research Rust async traits"
jarvis "clean this pdf for notebooklm"

# Knowledge Retrieval (RAG)
jarvis query "How does the indexing pipeline work?"
```

### 3. API Endpoints
Jarvis exposes a lightweight HTTP API for programmatic interaction. All endpoints are accessible via `curl` or any HTTP client:

| Endpoint         | Description                                                                 |
|------------------|-----------------------------------------------------------------------------|
| **`/chat`**      | Natural language tasking with LLMs (e.g., `curl -X POST http://localhost:8000/chat -d '{"query": "explain Rust lifetimes"}'`) |
| **`/fix`**       | Code fix suggestions (e.g., `curl -X POST http://localhost:8000/fix -d '{"code": "fn main() { println!(); }"}`) |
| **`/explain`**   | Detailed explanation of code or concepts (e.g., `curl -X POST http://localhost:8000/explain -d '{"topic": "Rust ownership model"}'`) |
| **`/index`**     | Index codebases or documents for RAG (e.g., `curl -X POST http://localhost:8000/index -d '{"path": "/home/user/codebase"}`) |
| **`/cancel`**    | Cancel ongoing tasks or processes                                             |
| **`/analyze_error`** | Analyze and suggest fixes for errors in code or logs                     |
| **`/summarize_git`** | Generate a summary of Git history and changes                             |
| **`/research_manual`** | Manual research mode for deep-dive analysis                             |
| **`/prefetch`**  | Prefetch data or resources for upcoming tasks                                |

---

## 🛠️ Tech Stack
- **Languages**: Python 3.12, Rust (Ratatui TUI), Lua (Neovim Integration).
- **Inference**: Ollama (CPU-only optimized).
- **Search**: SearXNG.
- **Data**: SQLite, MinerU (PDF processing).

---

## 🛡️ Backup & Portability
Keep your AI's memory and logic safe. Run the portable backup script:
```bash
./bin/backup.sh
```
This bundles both your code and your vault data into a single `JarvisData` directory.

---
*Created by Antigravity AI for the Jarvis Project.*