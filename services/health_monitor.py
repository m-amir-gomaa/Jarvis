#!/usr/bin/env python3
# /home/qwerty/NixOSenv/Jarvis/services/health_monitor.py (Enhanced with Watchdog & Eco Mode)
import os
import time
import subprocess
from pathlib import Path

# Try importing psutil for resource monitoring
try:
    import psutil
except ImportError:
    psutil = None

# Configuration
_JARVIS_ROOT = Path(os.environ.get("JARVIS_ROOT", Path(__file__).resolve().parent.parent))
PAUSE_FILE   = _JARVIS_ROOT / "logs" / "pause_time.tmp"
# Default Configuration (Fallback)
RESOURCE_CHECK_INTERVAL = 60
DEFAULT_NOTIFICATION_INTERVAL = 300
DEFAULT_RAM_THRESHOLD_MB = 1024
DEFAULT_CPU_THRESHOLD_PCT = 90

# Services to monitor (excluding health-monitor itself)
SERVICES = [
    "jarvis-git-monitor.service",
    "jarvis-coding-agent.service",
    "jarvis-self-healer.service",
    "jarvis-lsp.service",
    "jarvis-voice-gateway.service",
    "jarvis-daily-digest.timer",
    "jarvis-context-updater.timer",
]

def check_pause_duration(interval_sec: int):
    """Notify if AI has been paused for a long time."""
    if os.path.exists(PAUSE_FILE):
        try:
            with open(PAUSE_FILE, "r") as f:
                pause_time = int(f.read().strip())
            
            elapsed = time.time() - pause_time
            if elapsed > interval_sec:
                subprocess.run(["notify-send", "-u", "critical", "Jarvis Warning", f"AI has been paused for {int(elapsed/60)} minutes. System idle? Consider resuming."])
                # Reset time to avoid spamming every second (will notify every interval again)
                with open(PAUSE_FILE, "w") as f:
                    f.write(str(int(time.time())))
                    
        except Exception as e:
            print(f"Error checking pause: {e}")

def check_services_watchdog():
    """Detect and restart failed services."""
    for svc in SERVICES:
        try:
            result = subprocess.run(["systemctl", "--user", "is-failed", svc], capture_output=True, text=True)
            if result.stdout.strip() == "failed":
                print(f"[Watchdog] Service {svc} failed. Attempting restart...")
                subprocess.run(["systemctl", "--user", "restart", svc])
                subprocess.run(["notify-send", "Jarvis Watchdog", f"Service {svc} crashed and was restarted."])
        except Exception as e:
            print(f"Watchdog error for {svc}: {e}")

def check_resources(ram_thresh_mb: int, cpu_thresh_pct: int):
    """Monitor system RAM and CPU."""
    if not psutil:
        return

    try:
        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=1)
        
        # RAM check
        if mem.available < (ram_thresh_mb * 1024 * 1024):
            subprocess.run(["notify-send", "-u", "critical", "Jarvis Resource Alert", 
                             f"Low System RAM! {mem.available // (1024*1024)}MB available."])
        
        # CPU check
        if cpu > cpu_thresh_pct:
            subprocess.run(["notify-send", "Jarvis Resource Alert", 
                             f"High CPU Load ({cpu}%). System performance may be degraded."])
            
    except Exception as e:
        print(f"Resource check error: {e}")

def main():
    print("Jarvis Smart Health Monitor started...")
    
    # Optional: Initial pulse via event bus if available
    try:
        from lib.event_bus import emit
        has_bus = True
    except ImportError:
        has_bus = False

    while True:
        try:
            from lib.prefs_manager import PrefsManager
            pm = PrefsManager()
            
            # Load dynamic config
            ram_thresh = pm.get("services.health_monitor.ram_threshold_mb", DEFAULT_RAM_THRESHOLD_MB)
            cpu_thresh = pm.get("services.health_monitor.cpu_threshold_pct", DEFAULT_CPU_THRESHOLD_PCT)
            notif_interval = pm.get("services.health_monitor.notification_interval_sec", DEFAULT_NOTIFICATION_INTERVAL)
            
            # Pass config to checks
            check_pause_duration(notif_interval)
            check_services_watchdog()
            check_resources(ram_thresh, cpu_thresh)
            
            if has_bus:
                emit('health_monitor', 'pulse', {'status': 'ok'})
                
        except Exception as e:
            print(f"Main loop error: {e}")
            
        time.sleep(RESOURCE_CHECK_INTERVAL)

if __name__ == "__main__":
    main()
