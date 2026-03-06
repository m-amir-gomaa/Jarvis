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

- **Hierarchical Knowledge**: A 3-layer RAG system that prioritizes local documentation and theory over generic web noise.
- **Agentic Loops**: Self-correcting pipelines for NixOS configuration and Python development—if it breaks, Jarvis diagnoses and fixes it.
- **Episodic Memory**: A unified `events.db` that tracks your daily activity, allowing Jarvis to stay contextually aware of your work week.
- **Research Agent**: Automated technical research using a self-hosted **SearXNG** engine, summarizing findings directly into Markdown.
- **TUI Dashboard**: A high-performance Rust dashboard (`jarvis-monitor`) for real-time monitoring of service health and inference metrics.

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

### 3. Documentation
- **User Manual**: Run `jarvis man` in your terminal.
- **Specs & Roadmap**: Consult the [Merged Specs](./docs/JARVIS_Specs_and_Roadmap_Final_Merged.md) for deep technical details.

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
