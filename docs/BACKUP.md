# Jarvis Maintenance & Backup Guide

Jarvis relies on persistent data stored in the Vault. Protecting this data is critical for system reliability.

## 1. The Vault Structure

All runtime data resides in `/THE_VAULT/jarvis/`:
- `databases/`: SQLite files for security, knowledge, and events.
- `context/`: Active session tokens and runtime state.
- `logs/`: Diagnostic logs for all services.
- `secrets/`: Encrypted keyring for external API keys.

## 2. Automated Backups

Jarvis includes a `bin/backup.sh` script to automate data protection.

### Simple Backup
Copies the repository and the Vault data to the backup directory:
```bash
make backup
# OR
bash bin/backup.sh
```

### Full Archival
Compresses the entire environment (including large models and venv) for disaster recovery:
```bash
make archive
# OR
bash bin/backup.sh --archive
```

## 3. Database Maintenance

The SQLite databases can grow over time. We recommend periodic cleanup:
```bash
# Clean application logs
make clean-logs
```

## 4. Disaster Recovery

To restore from a backup:
1. Ensure `/THE_VAULT/jarvis` exists.
2. Unpack the backup archive to the expected target location.
3. Re-initialize the virtual environment using `make setup`.
4. Run `jarvis status` to verify service availability.
