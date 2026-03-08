# 📟 Jarvis Interaction Interfaces

Jarvis is designed to be accessible wherever you are: in the terminal, in your code editor, or even across the room via voice. This guide explains how to use each interface effectively.

---

## 💻 1. The CLI Interface (`jarvis.py`)

The CLI is the "brain stem" of the system. It handles management, manual queries, and security approvals.

### Natural Language Mode
Simply pass a prompt in quotes to Jarvis:
```bash
jarvis "Explain how my NixOS configuration handles systemd services"
```
Jarvis will classify your intent and trigger the appropriate ERS chain.

### Subcommand Mode
For explicit control, use standard subcommands:
- `jarvis status`: System health and service check.
- `jarvis start / stop`: Manage background daemons.
- `jarvis pending`: View and approve capability requests.
- `jarvis associate [cat]`: Link the current directory to a knowledge category.
- `jarvis log show [--lines N]`: Display recent structured system logs.
- `jarvis snapshot [list|create|restore]`: Manage point-in-time vault backups.

> [!TIP]
> **Cascading Configuration**: Jarvis CLI automatically resolves settings from global, workspace, and local `.jarvis/config.toml` files. Use `jarvis status` to see the currently active configuration.

---

## ⌨️ 2. The Neovim IDE Integration

Jarvis lives inside Neovim as a custom LSP server, providing deep context-aware coding assistance.

### Keybindings (Default Setup)
- `<leader>ji`: **Initialize** connection and authenticate.
- `<leader>je`: **Explain** the current selection or function.
- `<leader>jr`: **Refactor** the selected code with least-privilege security.
- `<leader>jm`: **Manage Models** — switch AI backends dynamically.
- `<leader>jf`: **Fix** the error at the cursor (LSP diagnostic integration).
- `<leader>jc`: **Chat** with Jarvis (streaming RAG chat).
- `<leader>jt`: **MCP Tools** — Browse and execute external tools via the Telescope picker.
- `:JarvisPin`: **Pin Context** — add selection to persistent agent context.
- `:JarvisTimeline`: **Show Timeline** — view history for the current file.
- `:JarvisInlineRefactor`: **Inline Streaming Edit** — refactor code in-place.

### Debugging Keybindings
- `<F5>`: **DAP Continue** — start or continue debugging.
- `<F10>`/`<F11>`: **Step Over/Into** — debug navigation.
- `b`: **Toggle Breakpoint** — set/unset debug breakpoints.

### Inline Completion
Jarvis provides ghost-text completions (like GitHub Copilot) powered by your local `qwen2.5-coder` model.
- `Tab`: Accept the completion.
- `Ctrl-]`: Manually trigger a completion request.

*For expert workflows, see the [Advanced Neovim Guide](ADVANCED_NEOVIM.md).*

---

## 📊 3. The Dashboard TUI (`jarvis-monitor`)

A high-performance Rust monitor built with `ratatui` for real-time visibility.

Launch via:
```bash
jarvis dashboard
```

### Tabs & Views
1.  **Dashboard**: General system health, load averages, and the latest LLM event log.
2.  **Security**: The "Glass Box." A live audit trail of every file read, shell command, and network request made by the agents.
3.  **ERS**: Real-time progress bars and step outputs for active reasoning chains.
4.  **IDE**: Status of active Neovim connections and session tokens.

---

## 🎙️ 4. Voice Commands (Hands-Free)

Jarvis features a low-latency voice gateway powered by `whisper.cpp`.

### Activation
By default, the voice gateway is managed by the main systemd unit. You can toggle it via the CLI:
```bash
jarvis toggle voice
```

### Usage
Jarvis listens for wake words: **"Jarvis"**, **"Assistant"**, or **"Hey"**.
- *"Hey Jarvis, summarize my git commits for the last hour."*
- *"Jarvis, status report."*

### Technical Detail
- **Engine**: `whisper-stream` running locally.
- **Model**: `ggml-base.en.bin` (optimized for fast CPU inference).
- **Latency**: Sub-second transcription on standard i7 CPUs.

---

## 🛠️ 5. Background Services (Systemd)

On NixOS, Jarvis runs as a set of user-level systemd units. You can monitor them directly:
```bash
systemctl --user status jarvis-health-monitor
systemctl --user status jarvis-coding-agent
systemctl --user status jarvis-git-monitor
systemctl --user status jarvis-mcp-server
```

---

*For the full list of keybindings, see the [Interaction Interfaces](INTERFACES.md) guide and the [Man Page](jarvis.1).*
