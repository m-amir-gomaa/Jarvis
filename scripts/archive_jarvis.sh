#!/usr/bin/env bash
# /home/qwerty/NixOSenv/Jarvis/scripts/archive_jarvis.sh
# Comprehensive Archival Script for Jarvis (Code + Vault Data)

set -e

# Configuration
CODE_DIR="/home/qwerty/NixOSenv/Jarvis"
VAULT_DIR="/THE_VAULT/jarvis"
BACKUP_ROOT="/home/qwerty/Backups/Jarvis"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
ARCHIVE_NAME="jarvis_backup_$TIMESTAMP.tar.gz"
DEST_PATH="$BACKUP_ROOT/$ARCHIVE_NAME"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_ROOT"

echo "[*] Starting Jarvis Archival..."
echo "    Timestamp: $TIMESTAMP"
echo "    Destination: $DEST_PATH"

# Temporary directory for staging
STAGING_DIR=$(mktemp -d)
trap 'rm -rf "$STAGING_DIR"' EXIT

echo "[*] Staging codebase (excluding heavy build artifacts)..."
# We use rsync to stage while excluding .venv, target, and pycache
rsync -a "$CODE_DIR/" "$STAGING_DIR/code/" \
    --exclude ".venv" \
    --exclude "target" \
    --exclude "__pycache__" \
    --exclude ".git" \
    --exclude "*.pyc"

echo "[*] Staging vault data (databases, logs, prompts)..."
rsync -a "$VAULT_DIR/" "$STAGING_DIR/vault/" \
    --exclude ".venv" \
    --exclude "tmp"

echo "[*] Compressing archive..."
tar -czf "$DEST_PATH" -C "$STAGING_DIR" .

# Calculate size
SIZE=$(du -h "$DEST_PATH" | cut -f1)

echo "[+] Done! Jarvis archived successfully."
echo "    File: $DEST_PATH"
echo "    Size: $SIZE"
echo ""
echo "To restore:"
echo "  tar -xzf $ARCHIVE_NAME -C /desired/restore/path"
