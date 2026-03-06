#!/usr/bin/env bash
# Jarvis Status Report Generator

echo "===================================================="
echo "          JARVIS SYSTEM STATUS REPORT               "
echo "===================================================="
echo "Timestamp: $(date)"
echo ""

# 1. Service Status
echo "--- Services ---"
printf "%-25s | %-15s\n" "Service Name" "Status"
printf "%-25s | %-15s\n" "-------------------------" "---------------"
for svc in jarvis-coding-agent jarvis-git-monitor jarvis-health-monitor jarvis-self-healer; do
    status=$(systemctl --user is-active $svc 2>/dev/null || echo "not-found")
    printf "%-25s | %-15s\n" "$svc" "$status"
done
echo ""

# 2. Storage Status
echo "--- Storage (SSD/HDD) ---"
df -h / /THE_VAULT 2>/dev/null | grep -v "Filesystem" | awk '{printf "%-15s | Size: %-6s | Used: %-6s | Avail: %-6s | Use%%: %-4s\n", $6, $2, $3, $4, $5}'
echo ""

# 3. Backup Status
echo "--- Latest Backups ---"
if [ -d "/home/qwerty/Backups/Jarvis" ]; then
    echo "SSD Backup Directory: Found"
    ls -lt /home/qwerty/Backups/Jarvis/jarvis_backup_*.tar.gz 2>/dev/null | head -n 1 | awk '{print "Last Archive (SSD): " $6 " " $7 " " $8}'
else
    echo "SSD Backup Directory: Not Found"
fi

if [ -d "/THE_VAULT/JarvisBackups" ]; then
    echo "HDD Backup Directory: Found"
    ls -lt /THE_VAULT/JarvisBackups/jarvis_backup_*.tar.gz 2>/dev/null | head -n 1 | awk '{print "Last Archive (HDD): " $6 " " $7 " " $8}'
else
    echo "HDD Backup Directory: Not Found"
fi
echo ""

echo "===================================================="
