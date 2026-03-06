# Jarvis Installation Guide

Jarvis is a local-first AI coding assistant. This guide covers installation on NixOS (recommended) and other Linux environments.

---

## 1. NixOS

### 1a. Personal / `~/NixOSenv` Setup *(my configuration)*

This is the canonical setup used in development. The repository lives inside `~/NixOSenv` and is managed via a Home Manager + Flake configuration.

**Structure:**
```
~/NixOSenv/
  Jarvis/             ← source code, Nix modules, Lua config (SSD)
    index/            ← HOT METADATA: codebase.db (SSD - high speed)
  modules/jarvis.nix  ← systemd service definitions
/THE_VAULT/jarvis/    ← bulk runtime vault (HDD): .venv, data, logs
/THE_VAULT/JarvisData/ ← unified backup bundle
```

**Prerequisites:**
- NixOS with Flakes enabled
- Home Manager configured
- SSD partition for `~/NixOSenv` (Core)
- Large HDD partition mounted at `/THE_VAULT` (Bulk)

**Steps:**
1. **Clone inside `NixOSenv` (SSD):**
   ```bash
   git clone git@github.com:m-amir-gomaa/Jarvis.git ~/NixOSenv/Jarvis
   ```

2. **Import the Jarvis module in `configuration.nix`:**
   ```nix
   imports = [ ./modules/jarvis.nix ];
   ```

3. **Rebuild:**
   ```bash
   sudo nixos-rebuild switch --flake ~/NixOSenv#nixos
   ```

4. **Set up the runtime vault (HDD):**
   ```bash
   sudo mkdir -p /THE_VAULT/jarvis
   sudo chown $USER /THE_VAULT/jarvis
   cd /THE_VAULT/jarvis && python -m venv .venv
   source .venv/bin/activate && pip install requests numpy watchdog aiohttp rank_bm25 filelock 'mineru[pipeline]'
   ```

5. **Migrate Metadata (for existing users):**
   If you have an existing `codebase.db` on your HDD, run the migrator:
   ```bash
   bash ~/NixOSenv/Jarvis/scripts/index_migrator.sh
   ```

6. **Pull the required Ollama models:**
   ```bash
   ollama pull qwen2.5-coder:14b
   ollama pull qwen3:1.7b
   ollama pull nomic-embed-text:latest
   ```

---

### 1b. Generic NixOS Setup *(for other developers)*

Use this if you have a different directory layout or don't use `~/NixOSenv`.

**Prerequisites:**
- NixOS with Flakes enabled
- `git` installed
- A `configuration.nix` you can modify (standalone or in any flake)

**Steps:**
1. **Clone anywhere you prefer:**
   ```bash
   git clone git@github.com:m-amir-gomaa/Jarvis.git ~/Jarvis
   cd ~/Jarvis
   ```

2. **Copy `jarvis.nix` into your NixOS modules:**
   ```bash
   cp modules/jarvis.nix /path/to/your/nixos/modules/jarvis.nix
   ```
   Then edit `jarvis.nix` and update `JARVIS_ROOT` and `VAULT_DIR` to match your actual paths.

3. **Import the module in your `configuration.nix`:**
   ```nix
   imports = [
     ./path/to/your/modules/jarvis.nix
   ];
   ```

4. **Rebuild:**
   ```bash
   sudo nixos-rebuild switch --flake /path/to/your/flake#hostname
   ```

5. **Set up the runtime directory and models** (same as step 4–5 above, adjust paths).

> **Note:** Without Home Manager you'll need to set `PYTHONPATH` and shell aliases manually. See `docs/BOOTSTRAP.md` for details.

---

## 2. Non-NixOS with Nix Package Manager

If you're on Ubuntu, Fedora, etc. but have the Nix package manager installed:

```bash
git clone git@github.com:m-amir-gomaa/Jarvis.git Jarvis
cd Jarvis
nix-shell
make setup
```

---

## 3. Non-NixOS (Plain Linux)

**Prerequisites:** Python 3.10+, `pip`, `make`, `ollama`, optionally `searxng`.

```bash
git clone git@github.com:m-amir-gomaa/Jarvis.git Jarvis
cd Jarvis
python -m venv .venv
source .venv/bin/activate
pip install requests numpy watchdog aiohttp rank_bm25 filelock 'mineru[pipeline]'
export PYTHONPATH=$(pwd)
```

---

## 4. Backup & Portability

Run the bundled backup script to create a portable snapshot:

```bash
bash bin/backup.sh
```

This syncs:
1. **Code** → `JarvisData/code/` (SSD source)
2. **Hot Indices** → `JarvisData/index/` (SSD metadata)
3. **Vault Data** → `JarvisData/data/` (HDD bulk)

For a full list of data locations that need manual USB/Syncthing sync (databases, model weights, indexes), see **[docs/BACKUP_GUIDE.md](docs/BACKUP_GUIDE.md)**.
