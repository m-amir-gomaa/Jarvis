#!/usr/bin/env bash

# Jarvis Portable Backup Script
# ─────────────────────────────────────────────────────────────────────────────
# Backs up Jarvis code + runtime data into JarvisData/ next to the runtime dir.
#
# Runtime dir : /THE_VAULT/jarvis
# Backup dir  : /THE_VAULT/JarvisData   (parent of runtime dir)
#
# Layout:
#   /THE_VAULT/JarvisData/
#     code/   ← rsync of repo (~/NixOSenv/Jarvis), no .git or build artefacts
#     data/   ← rsync of runtime vault (/THE_VAULT/jarvis), no .venv or target/
# ─────────────────────────────────────────────────────────────────────────────

# Jarvis runtime root
RUNTIME_DIR="/THE_VAULT/jarvis"
# Backup lives in the parent of the runtime dir
BACKUP_DIR="$(dirname "$RUNTIME_DIR")/JarvisData"
BACKUP_CODE="$BACKUP_DIR/code"
BACKUP_DATA="$BACKUP_DIR/data"

# Jarvis source repo (code lives here, not on the vault)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JARVIS_REPO="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "────────────────────────────────────────────"
echo "  Jarvis Portable Backup"
echo "  Code  : $JARVIS_REPO  →  $BACKUP_CODE"
echo "  Data  : $RUNTIME_DIR  →  $BACKUP_DATA"
echo "────────────────────────────────────────────"

# Create backup directories
mkdir -p "$BACKUP_CODE"
mkdir -p "$BACKUP_DATA"

# 1. Back up Source Code (The Repo)
echo "[1/2] Syncing source code..."
rsync -ah --delete \
    --exclude=".git" \
    --exclude="node_modules" \
    --exclude="__pycache__" \
    --exclude="*.pyc" \
    --exclude="target/" \
    "$JARVIS_REPO/" "$BACKUP_CODE/"

# 2. Back up Runtime Data (The Vault)
if [ -d "$RUNTIME_DIR" ]; then
    echo "[2/2] Syncing runtime data..."
    rsync -ah --delete \
        --exclude=".venv" \
        --exclude="target/" \
        --exclude="__pycache__" \
        --exclude="*.pyc" \
        "$RUNTIME_DIR/" "$BACKUP_DATA/"
else
    echo "[2/2] Warning: $RUNTIME_DIR not found. Skipping vault backup."
fi

echo "────────────────────────────────────────────"
echo "  Backup complete → $BACKUP_DIR"
echo "────────────────────────────────────────────"
