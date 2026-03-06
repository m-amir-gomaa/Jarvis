# Jarvis Backup & Manual Sync Guide

The Jarvis GitHub repository contains **only code and configuration**. The following runtime data is excluded and must be backed up manually via USB or Syncthing.

---

## Data Requiring Manual Backup

| Item | Description | Path |
| :--- | :--- | :--- |
| **RAG Knowledge Base** | 3-Layer hierarchical knowledge (Layers 1–3) | `/THE_VAULT/jarvis/data/knowledge.db` |
| **Episodic Index** | Codebase and file index for local RAG context | `/THE_VAULT/jarvis/data/file_index.json` |
| **Episodic Memory** | Activity logs and daily digest history | `/THE_VAULT/jarvis/logs/events.db` |
| **Inbox Cache** | Metadata for processed inbox/document items | `/THE_VAULT/jarvis/data/inbox_cache.json` |
| **Ollama Model Weights** | Locally pulled LLM weights (large files) | `~/.ollama/models/` |

---

## Backup Script

The bundled script handles code and data in one pass:

```bash
bash bin/backup.sh
```

**Output:** `/THE_VAULT/JarvisData/`
```
JarvisData/
  code/   ← rsync of ~/NixOSenv/Jarvis (no .git, no build artefacts)
  data/   ← rsync of /THE_VAULT/jarvis  (no .venv, no target/)
```

---

## Declarative Configuration (NixOS)

Your system configuration is version-controlled separately:

| Component | File | Repo |
| :--- | :--- | :--- |
| Systemd services | `modules/jarvis.nix` | `NixOSenv` |
| Shell & aliases | `home.nix` → `programs.zsh` | `NixOSenv` |
| Dotfiles (p10k, completions) | `dotfiles/` | `NixOSenv` |

---

## Recommended Strategy

1. **Frequently**: `git push` both `NixOSenv` and `Jarvis` repos.
2. **Weekly/Monthly**: Run `bin/backup.sh` and copy `/THE_VAULT/JarvisData/` to an encrypted external drive.
3. **Cross-device sync**: Use Syncthing to mirror `/THE_VAULT/jarvis/data/` between machines automatically.

> The code is the brain's *logic*; the databases are its *memory*. Protect both.
