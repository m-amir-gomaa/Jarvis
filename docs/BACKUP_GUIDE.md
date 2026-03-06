# Jarvis Backup & Archival Guide

The Jarvis system consists of two main components: the **Codebase** (logic) and the **Vault** (memory).

---

## Unified Backup System

Jarvis now provides a centralized way to manage backups via `bin/backup.sh` or directly through the `jarvis` CLI.

### 1. Sync Mode (Snapshot)
Maintains mirrored copies of the codebase and vault data on both the SSD (Home) and the redundant HDD.

- **Command:** `jarvis backup`
- **SSD Output:** `~/Backups/Jarvis/JarvisData/`
- **HDD Output:** `/THE_VAULT/JarvisBackups/JarvisData/`

### 2. Archive Mode (Compressed)
Creates a timestamped `.tar.gz` archive on the SSD and automatically copies a redundant version to the HDD.

- **Command:** `jarvis archive`
- **SSD Output:** `~/Backups/Jarvis/jarvis_backup_YYYYMMDD_HHMMSS.tar.gz`
- **HDD Output:** `/THE_VAULT/JarvisBackups/jarvis_backup_YYYYMMDD_HHMMSS.tar.gz`

---

## Restoration Guide

If you need to restore from an archive, use the following commands (replace `[FILE]` with your archive name):

1. **Restore Codebase:**
   ```bash
   tar -xzf [FILE] -C ~/NixOSenv/Jarvis --strip-components=1 code
   ```

2. **Restore Vault Data:**
   ```bash
   tar -xzf [FILE] -C /THE_VAULT/jarvis --strip-components=1 vault
   ```

---

## Recommended Strategy

1. **Daily**: `git push` both `NixOSenv` and `Jarvis` repos.
2. **Weekly**: Run `jarvis backup` to refresh the local snapshot.
3. **Monthly**: Run `jarvis archive` and move to an external drive.

> "The code is the brain's logic; the databases are its memory. Protect both."
