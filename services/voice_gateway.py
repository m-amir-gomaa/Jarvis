#!/usr/bin/env python3
"""
Voice Gateway (Phase 7.3)
/home/qwerty/NixOSenv/Jarvis/services/voice_gateway.py

Listens for voice input using whisper.cpp (whisper-stream) and triggers Jarvis commands.
"""

import os
import sys
import subprocess
import signal
import re
from pathlib import Path

# Runtime paths
BASE_DIR = Path(os.environ.get("JARVIS_ROOT", Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(BASE_DIR))

WHISPER_BIN = str(BASE_DIR / "whisper-cpp-out" / "bin" / "whisper-stream")
MODEL_PATH = str(BASE_DIR / "models" / "whisper" / "ggml-base.en.bin")
JARVIS_BIN = str(BASE_DIR / "jarvis.py")
VENV_PY = str(BASE_DIR / ".venv" / "bin" / "python")

def handle_transcription(text: str):
    text = text.strip()
    if not text:
        return
        
    # Remove whisper-cpp artifacts like [BLANK_AUDIO] or [MUSIC]
    text = re.sub(r'\[.*?\]', '', text).strip()
    # Remove leading timestamps like "00:00:00.000 -> 00:00:03.000"
    text = re.sub(r'^\d{2}:\d{2}:\d{2}\.\d{3} -> \d{2}:\d{2}:\d{2}\.\d{3}', '', text).strip()
    
    if len(text) < 3:
        return
        
    print(f"\n[Voice] Transcribed: '{text}'")
    
    # Trigger Jarvis if it starts with 'Jarvis' or matches assistant keywords
    if any(keyword in text.lower() for keyword in ["jarvis", "assistant", "hey"]):
        # Clean prefix
        clean_text = re.sub(r'^(jarvis|assistant|hey)[,:\s]*', '', text, flags=re.IGNORECASE).strip()
        if not clean_text:
            return
            
        print(f"[Voice] Triggering Jarvis with: '{clean_text}'")
        try:
            # We call jarvis.py with the transcribed text
            # We use subprocess.Popen to not block the listener
            subprocess.Popen([VENV_PY, JARVIS_BIN, clean_text], env={**os.environ, "PYTHONPATH": str(BASE_DIR)})
        except Exception as e:
            print(f"[Voice] Failed to trigger Jarvis: {e}")

def is_voice_enabled():
    import tomllib
    pref_path = BASE_DIR / "config" / "preferences.toml"
    if not pref_path.exists():
        return True
    try:
        with open(pref_path, "rb") as f:
            prefs = tomllib.load(f)
            return prefs.get("preferences", {}).get("voice_enabled", True)
    except Exception:
        return True

def main():
    if not is_voice_enabled():
        print("[Voice] Voice commands are disabled in preferences.toml. Exiting.")
        sys.exit(0)
        
    if not os.path.exists(WHISPER_BIN):
        print(f"Error: whisper-stream not found at {WHISPER_BIN}")
        sys.exit(1)
        
    if not os.path.exists(MODEL_PATH):
        print(f"Error: Model not found at {MODEL_PATH}")
        sys.exit(1)

    print(f"[Voice] Starting voice gateway with model {Path(MODEL_PATH).name}")
    print("[Voice] Listening... (Use 'Jarvis, <command>' or 'Hey Jarvis, <command>')")
    
    # Run whisper-stream
    # -kc: keep-context
    # -t: threads
    # -step 3000: segment every 3 seconds
    # -vth 0.6: VAD threshold
    cmd = [
        WHISPER_BIN,
        "-m", MODEL_PATH,
        "-t", "4",
        "--step", "3000",
        "--length", "10000",
        "-kc",
        "-vth", "0.6",
        "-l", "en"
    ]
    
    # Set SDL_VIDEODRIVER=dummy to avoid window creation if any
    env = {**os.environ, "SDL_VIDEODRIVER": "dummy"}
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env
    )
    
    try:
        for line in process.stdout:
            # whisper-stream output handling
            # It usually prints pieces as it transcribes
            if "-->" in line:
                # This is likely a timestamped transcription line
                parts = line.split("-->", 1)
                if len(parts) > 1:
                    # Further split by second timestamp part or just take the rest
                    rest = parts[1].split(" ", 1)
                    if len(rest) > 1:
                        handle_transcription(rest[1])
            elif not line.startswith("("): # Ignore some SDL/debug lines
                handle_transcription(line)
                
    except KeyboardInterrupt:
        print("\n[Voice] Stopping voice gateway...")
        process.send_signal(signal.SIGINT)
        process.wait()

if __name__ == "__main__":
    main()
