#!/usr/bin/env python3
# /home/qwerty/NixOSenv/Jarvis/services/health_monitor.py (Updated)
import os
import time
import subprocess
from lib.event_bus import emit

import os as _os
from pathlib import Path
_JARVIS_ROOT = Path(_os.environ.get("JARVIS_ROOT", Path(__file__).resolve().parent.parent))
PAUSE_FILE   = _JARVIS_ROOT / "logs" / "pause_time.tmp"
NOTIFICATION_INTERVAL = 300 # 5 minutes

def check_pause_duration():
    if os.path.exists(PAUSE_FILE):
        try:
            with open(PAUSE_FILE, "r") as f:
                pause_time = int(f.read().strip())
            
            elapsed = time.time() - pause_time
            if elapsed > NOTIFICATION_INTERVAL:
                subprocess.run(["notify-send", "-u", "critical", "Jarvis Warning", f"AI has been paused for {int(elapsed/60)} minutes. System idle? Consider resuming."])
                # Reset time to avoid spamming every second (will notify every 5 mins again)
                with open(PAUSE_FILE, "w") as f:
                    f.write(str(int(time.time())))
                    
        except Exception as e:
            print(f"Error checking pause: {e}")

def main():
    print("Jarvis Health Monitor started...")
    while True:
        check_pause_duration()
        # Other health checks (CPU/RAM) would go here
        emit('health_monitor', 'pulse', {'status': 'ok'})
        time.sleep(60)

if __name__ == "__main__":
    main()
