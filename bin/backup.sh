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
SSD_INDEX_DIR="/home/qwerty/NixOSenv/Jarvis/index"
VAULT_DIR="/THE_VAULT/jarvis"
SSD_BACKUP_ROOT="/home/qwerty/Backups/Jarvis"
HDD_BACKUP_ROOT="/THE_VAULT/JarvisBackups"
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
echo "  Jarvis Centralized ${MODE^} (Tiered Storage)"
echo "  Timestamp: $TIMESTAMP"
echo "────────────────────────────────────────────"

if [ "$MODE" == "sync" ]; then
    for DEST_ROOT in "$SSD_BACKUP_ROOT" "$HDD_BACKUP_ROOT"; do
        echo "[*] Syncing to: $DEST_ROOT"
        BACKUP_CODE="$DEST_ROOT/JarvisData/code"
        BACKUP_DATA="$DEST_ROOT/JarvisData/data"
        BACKUP_INDEX="$DEST_ROOT/JarvisData/index"

        mkdir -p "$BACKUP_CODE" "$BACKUP_DATA" "$BACKUP_INDEX"

        echo "    - Syncing codebase (SSD)..."
        rsync -ah --delete "${EXCLUDES[@]}" "$CODE_DIR/" "$BACKUP_CODE/"

        echo "    - Syncing hot indices (SSD)..."
        if [ -d "$SSD_INDEX_DIR" ]; then
          rsync -ah --delete "${EXCLUDES[@]}" "$SSD_INDEX_DIR/" "$BACKUP_INDEX/"
        fi

        if [ -d "$VAULT_DIR" ]; then
            echo "    - Syncing vault data (HDD)..."
            rsync -ah --delete "${EXCLUDES[@]}" "$VAULT_DIR/" "$BACKUP_DATA/"
        else
            echo "    - Warning: $VAULT_DIR not found. Skipping vault backup."
        fi
        echo ""
    done

    echo "────────────────────────────────────────────"
    echo "  Backup complete → SSD & HDD"
    echo "────────────────────────────────────────────"

else
    # Archive Mode
    ARCHIVE_NAME="jarvis_backup_$TIMESTAMP.tar.gz"
    SSD_PATH="$SSD_BACKUP_ROOT/$ARCHIVE_NAME"
    HDD_PATH="$HDD_BACKUP_ROOT/$ARCHIVE_NAME"
    
    mkdir -p "$SSD_BACKUP_ROOT" "$HDD_BACKUP_ROOT"

    STAGING_DIR=$(mktemp -d)
    trap 'rm -rf "$STAGING_DIR"' EXIT

    echo "[*] Staging files..."
    mkdir -p "$STAGING_DIR/code" "$STAGING_DIR/vault" "$STAGING_DIR/index"

    echo "    - Staging codebase (SSD)..."
    rsync -a "${EXCLUDES[@]}" "$CODE_DIR/" "$STAGING_DIR/code/"
    
    echo "    - Staging hot indices (SSD)..."
    if [ -d "$SSD_INDEX_DIR" ]; then
        rsync -a "${EXCLUDES[@]}" "$SSD_INDEX_DIR/" "$STAGING_DIR/index/"
    fi

    echo "    - Staging vault data (HDD)..."
    if [ -d "$VAULT_DIR" ]; then
        rsync -a "${EXCLUDES[@]}" "$VAULT_DIR/" "$STAGING_DIR/vault/"
    fi

    echo "[*] Compressing archive..."
    tar -czf "$SSD_PATH" -C "$STAGING_DIR" .

    echo "[*] Copying redundant archive to HDD..."
    cp "$SSD_PATH" "$HDD_PATH"

    SIZE=$(du -h "$SSD_PATH" | cut -f1)

    echo "[+] Done! Jarvis archived successfully (SSD + HDD)."
    echo "    File (SSD): $SSD_PATH"
    echo "    File (HDD): $HDD_PATH"
    echo "    Size: $SIZE"
    echo ""
    echo "To restore Jarvis (Tiered Storage):"
    echo ""
    echo "1. Restore Codebase (SSD):"
    echo "   tar -xzf $ARCHIVE_NAME -C $CODE_DIR --strip-components=1 code"
    echo ""
    echo "2. Restore Hot Indices (SSD):"
    echo "   tar -xzf $ARCHIVE_NAME -C $SSD_INDEX_DIR --strip-components=1 index"
    echo ""
    echo "3. Restore Vault Data (HDD):"
    echo "   tar -xzf $ARCHIVE_NAME -C $VAULT_DIR --strip-components=1 vault"
    echo "────────────────────────────────────────────"
fi
