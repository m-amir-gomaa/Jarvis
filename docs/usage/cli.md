# User Guide: CLI & Services

The Jarvis CLI (`jarvis`) is the central control point for services, knowledge management, and documentation synchronization.

## 🛠️ Service Management

Jarvis operates several background daemons on NixOS as Systemd user services.

| Command | Action |
| :--- | :--- |
| `jarvis start` | Start all Jarvis background services. |
| `jarvis stop` | Stop all Jarvis background services. |
| `jarvis restart` | Restart all services and synchronize assets. |
| `jarvis status` | Check health and connection status of all daemons. |

### Background Services
*   `jarvis-coding-agent`: The HTTP server (port 7002) for Neovim and external tools.
*   `jarvis-indexer`: Monitors file changes and updates the vector store.
*   `jarvis-lsp`: Provides intelligent code navigation and diagnostics.
*   `jarvis-voice-gateway`: Handles STT/TTS for voice-commanded coding.

## 🧠 Knowledge & RAG

| Command | Action |
| :--- | :--- |
| `jarvis index` | Trigger a manual index of the current directory. |
| `jarvis index --rebuild` | Delete the existing vector store and rebuild from scratch. |
| `jarvis query "query"` | Search the project knowledge base via CLI. |

## 🔄 Assets & Sync

| Command | Action |
| :--- | :--- |
| `jarvis sync` | Manually synchronize man pages and shell completions. |
| `jarvis doctor` | Run a diagnostic suite to check dependencies and paths. |

## ❄️ Environment

Jarvis is optimized for **NixOS**:
*   **Pathing**: Assets are stored in `~/.jarvis/`.
*   **SSD Optimization**: The FAISS index is stored on the primary SSD for maximum performance.
*   **Read-Only Safety**: The CLI automatically handles read-only Nix store paths during synchronization.
