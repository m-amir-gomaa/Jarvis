# Deployment: NixOS Service Infrastructure

Jarvis is designed to be a native NixOS citizen, utilizing Systemd user units for all background intelligence.

## ⚙️ Configuration (`modules/jarvis.nix`)

The core configuration is located in the `NixOSenv` repository. It defines:
1.  **Python Environment**: A consolidated `.venv` with all v3.5 dependencies.
2.  **Environment Variables**: `JARVIS_ROOT`, `OLLAMA_BASE_URL`, and `SEARXNG_URL`.
3.  **Systemd Units**:
    *   `jarvis-coding-agent.service` (binds to `127.0.0.1:7002`).
    *   `jarvis-indexer.service` (watchdog-based indexing).
    *   `jarvis-lsp.service`.
    *   `jarvis-voice-gateway.service`.

## 🚀 Activation

To apply the latest Jarvis service definitions:
1.  Update the flake: `nix flake update` (inside `~/NixOSenv`).
2.  Rebuild: `sudo nixos-rebuild switch --flake ~/NixOSenv#nixos`.

## 📊 Monitoring

View logs for any service:
```bash
journalctl --user -u jarvis-coding-agent -f
```

Check memory/CPU usage:
```bash
jarvis status
```

## 🔒 Security & Persistence

*   **Runtime Data**: Indices and caches are stored in `~/.jarvis/` to persist across NixOS generations.
*   **Sandboxing**: Services run with low-privilege user context, emphasizing "Admin Trust" ceiling as per the v3.5 specification.
