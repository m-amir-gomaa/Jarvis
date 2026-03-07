# Jarvis Installation Guide (V3)

This guide walks you through setting up Jarvis on a NixOS system.

## 1. Prerequisites

- **OS**: NixOS (Tiger Lake i7-1165G7 or similar CPU-bound hardware recommended).
- **RAM**: 16GB minimum (Ollama consumes ~9GB for 14B models).
- **Ollama**: Installed and running (`systemctl status ollama`).

## 2. Environment Setup

Jarvis uses a dedicated Python 3.12 virtual environment.

```bash
# From the repository root
make setup
```

This command:
1. Creates a `.venv` directory.
2. Installs dependencies from `requirements-v2.txt`.
3. Pre-installs `mineru` for document processing.

## 3. Vault Configuration

Jarvis stores heavy data and secrets in `/THE_VAULT/jarvis/`. Ensure this directory exists and is writable by your user.

```bash
sudo mkdir -p /THE_VAULT/jarvis/{databases,logs,context,secrets,backups}
sudo chown -R $USER:users /THE_VAULT/jarvis
```

## 4. Model Configuration

Jarvis is optimized for **Qwen3** models via Ollama.

```bash
# Pull the recommended models
ollama pull qwen3:14b-q4_K_M  # Primary reasoning
ollama pull qwen3:8b         # General chat
ollama pull qwen2.5-coder:7b # Coding tasks
ollama pull qwen3:1.7b       # Fast/Complete
```

Configure your aliases in `config/models.toml`.

## 5. Security Session

Jarvis requires an active session token for IDE integration.

```bash
# Run the CLI once to initialize the session
jarvis status
```

The token is stored securely at `/THE_VAULT/jarvis/context/active_session_token`.

## 6. Neovim Integration

Add the following to your `init.lua` or `plugins.lua`:

```lua
-- Using a plugin manager like lazy.nvim
{
  "m-amir-gomaa/Jarvis",
  config = function()
    require("jarvis").setup({
      -- Options
    })
  end
}
```

Ensure `jarvis-lsp` is started (`jarvis start` or manual systemd service).
