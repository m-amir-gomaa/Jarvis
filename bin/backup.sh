#!/usr/bin/env bash

# Jarvis Centralized Backup & Archival Script
# ─────────────────────────────────────────────────────────────────────────────
# Handles both rsync-based syncing (default) and .tar.gz archiving (--archive).
#
# Usage:
#   bash bin/backup.sh           # Sync to /THE_VAULT/JarvisData
#   bash bin/backup.sh --archive # Create .tar.gz in ~/Backups/Jarvis
# ─────────────────────────────────────────────────────────────────────────────

set -e

# Configuration
CODE_DIR="/home/qwerty/NixOSenv/Jarvis"
VAULT_DIR="/THE_VAULT/jarvis"
BACKUP_ROOT="/home/qwerty/Backups/Jarvis"
SYNC_DEST="$(dirname "$VAULT_DIR")/JarvisData"
HDD_DEST="/THE_VAULT/JarvisRedundant"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

MODE="sync"
if [[ "$1" == "--archive" || "$1" == "-a" ]]; then
    MODE="archive"
fi

# Common Exclusions
EXCLUDES=(
    "--exclude=.git"
    "--exclude=.venv"
    "--exclude=target"
    "--exclude=node_modules"
    "--exclude=__pycache__"
    "--exclude=*.pyc"
    "--exclude=tmp"
)

echo "────────────────────────────────────────────"
echo "  Jarvis Centralized ${MODE^}"
echo "  Timestamp: $TIMESTAMP"
echo "────────────────────────────────────────────"

if [ "$MODE" == "sync" ]; then
    for DEST in "$SYNC_DEST" "$HDD_DEST"; do
        echo "[*] Syncing to: $DEST"
        BACKUP_CODE="$DEST/code"
        BACKUP_DATA="$DEST/data"

        mkdir -p "$BACKUP_CODE" "$BACKUP_DATA"

        echo "    - Syncing codebase..."
        rsync -ah --delete "${EXCLUDES[@]}" "$CODE_DIR/" "$BACKUP_CODE/"

        if [ -d "$VAULT_DIR" ]; then
            echo "    - Syncing vault data..."
            rsync -ah --delete "${EXCLUDES[@]}" "$VAULT_DIR/" "$BACKUP_DATA/"
        else
            echo "    - Warning: $VAULT_DIR not found. Skipping vault backup."
        fi
        echo ""
    done

    echo "────────────────────────────────────────────"
    echo "  Backup complete → $SYNC_DEST & $HDD_DEST"
    echo "────────────────────────────────────────────"

else
    # Archive Mode
    ARCHIVE_NAME="jarvis_backup_$TIMESTAMP.tar.gz"
    DEST_PATH="$BACKUP_ROOT/$ARCHIVE_NAME"
    mkdir -p "$BACKUP_ROOT" "$HDD_DEST"

    STAGING_DIR=$(mktemp -d)
    trap 'rm -rf "$STAGING_DIR"' EXIT

    echo "[*] Staging files..."
    mkdir -p "$STAGING_DIR/code" "$STAGING_DIR/vault"

    rsync -a "${EXCLUDES[@]}" "$CODE_DIR/" "$STAGING_DIR/code/"
    if [ -d "$VAULT_DIR" ]; then
        rsync -a "${EXCLUDES[@]}" "$VAULT_DIR/" "$STAGING_DIR/vault/"
    fi

    echo "[*] Compressing archive..."
    tar -czf "$DEST_PATH" -C "$STAGING_DIR" .

    echo "[*] Copying redundant archive to HDD..."
    cp "$DEST_PATH" "$HDD_DEST/"

    SIZE=$(du -h "$DEST_PATH" | cut -f1)

    echo "[+] Done! Jarvis archived successfully (Primary + Redundant)."
    echo "    File (Primary): $DEST_PATH"
    echo "    File (Redundant): $HDD_DEST/$ARCHIVE_NAME"
    echo "    Size: $SIZE"
    echo ""
    echo "To restore Jarvis:"
    echo ""
    echo "1. Restore Codebase:"
    echo "   tar -xzf $ARCHIVE_NAME -C $CODE_DIR --strip-components=1 code"
    echo ""
    echo "2. Restore Vault Data:"
    echo "   tar -xzf $ARCHIVE_NAME -C $VAULT_DIR --strip-components=1 vault"
    echo "────────────────────────────────────────────"
fi
