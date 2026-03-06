#!/usr/bin/env bash
# Jarvis Log Maintenance Script

LOG_DIR="/home/qwerty/NixOSenv/Jarvis/logs"
DAYS=7

echo "[Jarvis] Cleaning logs older than $DAYS days in $LOG_DIR..."

if [ -d "$LOG_DIR" ]; then
    # Find and delete files older than 7 days
    find "$LOG_DIR" -type f -mtime +$DAYS -name "*.log" -delete
    find "$LOG_DIR" -type f -mtime +$DAYS -name "*.jsonl" -delete
    echo "[Jarvis] Log cleanup complete."
else
    echo "[Jarvis] Log directory not found: $LOG_DIR"
fi
