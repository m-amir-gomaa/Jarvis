#!/usr/bin/env bash

# Jarvis Portable Backup Script
# Creates a JarvisData directory in the parent directory of Jarvis

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Jarvis repo root
JARVIS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# Parent directory of Jarvis repo
PARENT_DIR="$(cd "$JARVIS_ROOT/.." && pwd)"
# Backup destination
BACKUP_DIR="$PARENT_DIR/JarvisData"
BACKUP_CODE="$BACKUP_DIR/code"
BACKUP_DATA="$BACKUP_DIR/data"

echo "------------------------------------------------"
echo "Jarvis Portable Backup"
echo "Target: $BACKUP_DIR"
echo "------------------------------------------------"

# Create backup directories
mkdir -p "$BACKUP_CODE"
mkdir -p "$BACKUP_DATA"

# 1. Back up Source Code (The Repo)
echo "Backing up source code from $JARVIS_ROOT..."
rsync -avh --exclude=".git" --exclude="node_modules" "$JARVIS_ROOT/" "$BACKUP_CODE/"

# 2. Back up Runtime Data (The Vault)
SOURCE_DATA="/THE_VAULT/jarvis"

if [ -d "$SOURCE_DATA" ]; then
    echo "Backing up runtime data from $SOURCE_DATA..."
    # Exclude .venv and target (for rust) to save space
    rsync -avh --exclude=".venv" --exclude="target" "$SOURCE_DATA/" "$BACKUP_DATA/"
else
    echo "Warning: $SOURCE_DATA not found. Skipping vault backup."
fi

echo "------------------------------------------------"
echo "Backup completed successfully!"
echo "Bundled at: $BACKUP_DIR"
echo "------------------------------------------------"
