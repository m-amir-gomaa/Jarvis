# Jarvis Porting & Decoupling Guide

This guide is for developers who want to bring Jarvis to Windows, non-Nix Linux distributions, or integrate it with IDEs other than Neovim.

## 1. Porting to Other OS/Distros

Jarvis V3 is heavily optimized for NixOS, but its core logic is standard Python. To port Jarvis, you must address the following areas:

### A. Dependency Management
- **Current**: Relies on `nix-shell` or Nix Flakes for reproducible environments.
- **Porting Step**: Create a standard `requirements.txt` or `pyproject.toml` for `pip`/`poetry`. 
- **Critical Dependencies**: `pydantic`, `fastapi`, `uvicorn`, `httpx`, `cryptography`, `jinja2`, `sqlite3`.

### B. Path Abstraction
- **Current**: Many scripts assume `/home/qwerty/NixOSenv/Jarvis` or `/THE_VAULT/jarvis`.
- **Porting Step**: Replace hardcoded paths with environment variables:
    - `JARVIS_ROOT`: The repository base.
    - `VAULT_ROOT`: The persistent data store.
- **Windows Note**: Ensure paths use `pathlib` for cross-platform compatibility (e.g., `\` vs `/`).

### C. System Services
- **Current**: Uses `systemd` user units for background daemons.
- **Porting Step**: 
    - **Windows**: Use Windows Services or a task runner like `NSSM`.
    - **Other Linux**: Use `OpenRC`, `runit`, or generic `docker-compose`.

### D. Hardware & Signals
- **Current**: Uses `SIGSTOP`/`SIGCONT` for pausing Ollama.
- **Porting Step**: 
    - **Windows**: Signal support is limited. You may need to use `subprocess.terminate()` or platform-specific process suspension APIs.
    - **Machine ID**: `SecretsManager` reads `/etc/machine-id`. On Windows, use a registry key or hardware UUID.

## 2. Decoupling from Neovim

Jarvis is designed to be "IDE-agnostic at heart" but currently has a strong "Antigravity-like" Neovim layer.

### A. The LSP Bridge
- The `services/jarvis_lsp.py` is a standard Language Server. Any IDE with an LSP client (VS Code, Emacs, JetBrains) can technically connect to it.
- **Decoupling Step**: Document the custom LSP extensions (e.g., `jarvis/get_capabilities`) so other IDE plugins can implement them.

### B. The HTTP Sidecar
- Jarvis runs a FastAPI server alongside the LSP. 
- **Decoupling Step**: Use the HTTP API for UI elements (like security prompts) instead of relying on Neovim's `vim.ui` or `input()`.
- **Endpoints to Leverage**:
    - `POST /chat`: General tasking.
    - `GET /security/pending`: Poll for OOB approvals.
    - `POST /security/approve`: Remote approval.

### C. Headless Execution
- Jarvis can run entirely in a "Server Mode" where it acts as a centralized AI brain for multiple clients.
- **Future Architecture**: Move all "IDE Specific" logic into `lib/ide/adapters/` and keep any logic related to "editing files" generic via a capability-based FS provider.

## 3. Roadblocks & PRs

We welcome Pull Requests that:
1. Replace `os.system()` calls with `subprocess.run(shell=False)`.
2. Abstract machine-specific identifiers.
3. Add `Dockerfile` support for containerized execution.
4. Implement a VS Code Extension that replicates the Antigravity-like features.

---
*For technical questions, please consult [docs/ARCHITECTURE.md](ARCHITECTURE.md).*
