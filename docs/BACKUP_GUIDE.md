# Jarvis Backup & Archival Guide

The Jarvis system consists of two main components: the **Codebase** (logic) and the **Vault** (memory).

---

## Unified Backup System

Jarvis now provides a centralized way to manage backups via `bin/backup.sh` or directly through the `jarvis` CLI.

### 1. Sync Mode (Snapshot)
Maintains mirrored copies of the codebase (SSD), hot indices (SSD), and vault data (HDD) on both backup drives.

- **Command:** `jarvis backup`
- **SSD Output:** `~/Backups/Jarvis/JarvisData/` (code, index, data)
- **HDD Output:** `/THE_VAULT/JarvisBackups/JarvisData/` (code, index, data)

### 2. Archive Mode (Compressed)
Creates a timestamped `.tar.gz` archive containing the full staggered system (SSD + HDD).

- **Command:** `jarvis archive`
- **SSD Output:** `~/Backups/Jarvis/jarvis_backup_YYYYMMDD_HHMMSS.tar.gz`
- **HDD Output:** `/THE_VAULT/JarvisBackups/jarvis_backup_YYYYMMDD_HHMMSS.tar.gz`

---

## Restoration Guide

If you need to restore from an archive, use the following commands:

1. **Restore Codebase (SSD):**
   ```bash
   tar -xzf [FILE] -C ~/NixOSenv/Jarvis --strip-components=1 code
   ```

2. **Restore Hot Indices (SSD):**
   ```bash
   tar -xzf [FILE] -C ~/NixOSenv/Jarvis/index --strip-components=1 index
   ```

3. **Restore Vault Data (HDD):**
   ```bash
   tar -xzf [FILE] -C /THE_VAULT/jarvis --strip-components=1 vault
   ```

---

## Recommended Strategy

1. **Daily**: `git push` both `NixOSenv` and `Jarvis` repos.
2. **Weekly**: Run `jarvis backup` to refresh the local snapshot.
3. **Monthly**: Run `jarvis archive` and move to an external drive.

> "The code is the brain's logic; the databases are its memory. Protect both."
