# Jarvis Installation Guide

Jarvis is a powerful AI coding assistant and system automation suite. This guide covers installation on various Linux environments.

## 1. NixOS (Recommended)

Jarvis is designed to integrate deeply with NixOS. A modular configuration is provided.

### Prerequisites
- NixOS with Flakes enabled.
- `git` installed.

### Steps
1. **Clone the repository**:
   ```bash
   git clone https://github.com/m-amir-gomaa/Jarvis.git ~/NixOSenv/Jarvis
   ```
2. **Import the module**:
   Add the following to your `configuration.nix`:
   ```nix
   imports = [
     ./modules/jarvis.nix # Path to the jarvis.nix module
   ];
   ```
3. **Apply the configuration**:
   ```bash
   sudo nixos-rebuild switch --flake ~/NixOSenv#nixos
   ```
4. **Pull Ollama Models**:
   ```bash
   ollama pull deepseek-coder:6.7b
   # or any other model you prefer
   ```

---

## 2. Non-NixOS with Nix Package Manager

If you are on a traditional Linux distribution (Ubuntu, Fedora, etc.) but have Nix installed.

### Steps
1. **Clone the repository**:
   ```bash
   git clone https://github.com/m-amir-gomaa/Jarvis.git Jarvis
   cd Jarvis
   ```
2. **Enter Nix Shell**:
   ```bash
   nix-shell
   ```
3. **Run Setup**:
   ```bash
   make setup
   ```

---

## 3. Non-NixOS without Nix

For systems using traditional package managers and standard Python environments.

### Prerequisites
- Python 3.10+
- `pip`
- `make`
- `ollama` (installed manually)
- `searxng` (optional, for research capabilities)

### Steps
1. **Clone the repository**:
   ```bash
   git clone https://github.com/m-amir-gomaa/Jarvis.git Jarvis
   cd Jarvis
   ```
2. **Create Virtual Environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. **Install Dependencies**:
   ```bash
   pip install requests numpy watchdog aiohttp rank_bm25 filelock
   pip install 'mineru[pipeline]'
   ```
4. **Configure Environment**:
   Ensure `PYTHONPATH` includes the Jarvis directory:
   ```bash
   export PYTHONPATH=$(pwd)
   ```

---

## Configuration & Structure (NixOS)

Jarvis utilizes a dual-directory structure on NixOS to separate source code from heavy runtime data:

- **Repository (`~/NixOSenv/Jarvis`)**: Contains the source code, Lua/Neovim config, and Nix modules. This is where you should commit and push changes.
- **Runtime Vault (`/THE_VAULT/jarvis`)**: This is the working directory for the system services. It contains the Python virtual environment (`.venv`), ingested data, indexes, and logs. This is located on the 744GB HDD to save space on the main drive.

The `modules/jarvis.nix` file is configured to execute code from the vault, but references the files in the repository for configuration.

---

## 4. Backup and Portability

To keep your Jarvis environment portable, use the refined backup script:

```bash
./bin/backup.sh
```

This script performs two clean actions:
1. **Source Code**: Backs up the `Jarvis` repository to `JarvisData/code`.
2. **Runtime Data**: Backs up the `/THE_VAULT/jarvis` data to `JarvisData/data` (excluding the virtual environment).

This ensures that even if you move machines, you have both your logic (code) and your memory (data) in one portable `JarvisData` bundle.
