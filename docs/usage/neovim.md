# User Guide: Neovim Plugin

Jarvis provides a premium, async-first Neovim integration powered by `plenary.nvim`.

## 🚀 Key Commands

| Command | Action |
| :--- | :--- |
| `:JarvisChat` | Open a RAG-augmented chat interface for the current project. |
| `:JarvisFix` | Analyzes errors in the current buffer and starts an agentic fix loop. |
| `:JarvisExplain` | Provides a deep explanation of the selected code or current buffer. |
| `:JarvisIndex` | Manually triggers a full semantic index of the current working directory. |
| `:JarvisCommit` | Generates a semantic git commit message based on staged changes. |
| `:JarvisSearch` | Performs a global web search using SearXNG and opens the results. |
| `:JarvisModel` | Interactive UI to switch model aliases (e.g., switch `chat` to Cloud). |
| `:JarvisCancel` | Aborts the current long-running Jarvis task (Fix/Chat/Search). |

## 🛠️ Configuration

### Requirements
*   `plenary.nvim` (for async HTTP requests).
*   `target: 127.0.0.1` (Connectivity is locked to IPv4 loopback for reliability).

### Installation (NixOS)
The plugin is automatically managed via the Jarvis Nix flake. Ensure your `modules/jarvis.nix` is up to date and you have run `sudo nixos-rebuild switch`.

### Troubleshooting
If Jarvis fails to connect:
1.  Check if the agent is running: `jarvis status`
2.  Verify port 7002: `ss -tulpn | grep 7002`
3.  Ensure you have restarted Neovim after a Jarvis update.

## 󱐋 Intelligence Features

### Auto-Prefetching
The plugin automatically primes models when you:
*   Open a source file (primes `chat` model).
*   Enter **Insert Mode** (primes `complete` model for instant FIM).

### Virtual Diagnostics
If you use `:JarvisExplainError` on a line with a compiler error, Jarvis will display an "instant fix" analysis as virtual text at the end of the line.
