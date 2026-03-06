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
JARVIS_ROOT="/home/qwerty/NixOSenv/Jarvis"
VAULT_DIR="/home/qwerty/NixOSenv/Jarvis" # Unified on SSD
HDD_BACKUP_ROOT="/THE_VAULT/JarvisBackups"
SSD_BACKUP_ROOT="/home/qwerty/Backups/Jarvis"
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
        BACKUP_DATA="$DEST_ROOT/JarvisData"

        mkdir -p "$BACKUP_DATA"

        echo "    - Syncing unified Jarvis (SSD to $(basename $DEST_ROOT))..."
        rsync -ah --delete "${EXCLUDES[@]}" "$JARVIS_ROOT/" "$BACKUP_DATA/"
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
    rsync -a "${EXCLUDES[@]}" "$JARVIS_ROOT/" "$STAGING_DIR/"

    echo "[*] Compressing archive..."
    tar -czf "$SSD_PATH" -C "$STAGING_DIR" .

    echo "[*] Copying redundant archive to HDD..."
    cp "$SSD_PATH" "$HDD_PATH"

    SIZE=$(du -h "$SSD_PATH" | cut -f1)

    echo "[+] Done! Jarvis archived successfully (Unified SSD)."
    echo "    File (SSD): $SSD_PATH"
    echo "    File (HDD): $HDD_PATH"
    echo "    Size: $SIZE"
    echo ""
    echo "To restore Jarvis (Unified SSD):"
    echo ""
    echo "   tar -xzf $ARCHIVE_NAME -C $JARVIS_ROOT"
    echo "────────────────────────────────────────────"
    echo "────────────────────────────────────────────"
fi
