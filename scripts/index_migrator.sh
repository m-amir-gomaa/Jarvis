#!/usr/bin/env bash
# /home/qwerty/NixOSenv/Jarvis/scripts/index_migrator.sh
# Migrates the "hot" codebase index from HDD to SSD for performance.

set -e

HDD_INDEX="/THE_VAULT/jarvis/index/codebase.db"
SSD_DIR="/home/qwerty/NixOSenv/Jarvis/index"
SSD_INDEX="$SSD_DIR/codebase.db"

echo "[Migrator] Starting Tiered Storage Migration..."

# 1. Create SSD index directory if missing
if [ ! -d "$SSD_DIR" ]; then
    echo "[Migrator] Creating SSD index directory: $SSD_DIR"
    mkdir -p "$SSD_DIR"
fi

# 2. Check if HDD index exists and SSD one doesn't
if [ -f "$HDD_INDEX" ] && [ ! -f "$SSD_INDEX" ]; then
    echo "[Migrator] Copying $HDD_INDEX to $SSD_INDEX (SSD)..."
    cp "$HDD_INDEX" "$SSD_INDEX"
    echo "[Migrator] Data migrated to SSD."
elif [ -f "$SSD_INDEX" ]; then
    echo "[Migrator] SSD index already exists. Skipping copy."
else
    echo "[Migrator] Error: Source index $HDD_INDEX not found."
    exit 1
fi

# 3. Create a symlink from HDD to SSD for backward compatibility
# (This ensures older scripts or hardcoded paths still work)
if [ -L "$HDD_INDEX" ]; then
    echo "[Migrator] Symlink already exists."
elif [ -f "$HDD_INDEX" ]; then
    echo "[Migrator] Backing up HDD index and creating symlink..."
    mv "$HDD_INDEX" "$HDD_INDEX.bak"
    ln -s "$SSD_INDEX" "$HDD_INDEX"
    echo "[Migrator] Symlink created: $HDD_INDEX -> $SSD_INDEX"
fi

echo "[Migrator] Migration complete. Jarvis is now using Tiered Storage."
