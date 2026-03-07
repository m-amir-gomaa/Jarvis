import os
import sys
from lib.event_bus import emit

# /home/qwerty/NixOSenv/Jarvis/lib/env_manager.py

REQUIRED_VARS = {
    'OLLAMA_BASE_URL':       ('http://localhost:11434', 'Ollama REST API endpoint'),
    'ANYTHINGLLM_BASE_URL':  ('http://localhost:3001',  'AnythingLLM REST API endpoint'),
    'ANYTHINGLLM_API_KEY':   (None,                     'AnythingLLM authentication key'),
    'GITEA_WEBHOOK_SECRET':  (None,                     'HMAC secret for Gitea webhooks'),
    'OPENROUTER_API_KEY':    (None,                     'OpenRouter API key for cloud LLMs'),
}

JARVIS_ROOT = os.environ.get("JARVIS_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_DIR = os.path.join(JARVIS_ROOT, "config")
DOTENV_PATH = os.path.join(CONFIG_DIR, ".env")
EXAMPLE_PATH = os.path.join(CONFIG_DIR, "env.example")

def load(required: list[str] = None) -> dict:
    """
    Loads environment variables from os.environ and fallback to .env file.
    Returns a dict with 'resolved' variables and 'missing' list if any.
    """
    # 1. Load /home/qwerty/NixOSenv/Jarvis/config/.env if it exists
    if os.path.exists(DOTENV_PATH):
        with open(DOTENV_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip("'").strip('"')
                    # os.environ takes priority
                    if key not in os.environ:
                        os.environ[key] = value

    # 2. Resolve each required var
    vars_to_check = required if required is not None else REQUIRED_VARS.keys()
    resolved = {}
    missing = []

    for var in vars_to_check:
        val = os.environ.get(var)
        desc = ""
        default = None
        
        if var in REQUIRED_VARS:
            default, desc = REQUIRED_VARS[var]
        
        if val is None:
            if default is not None:
                val = default
            else:
                missing.append((var, desc))
        
        resolved[var] = val
    
    return {"resolved": resolved, "missing": missing}

def validate_or_exit(required: list[str] = None):
    """
    Calls load(), prints a missing-vars table, and exits 1 if any required vars are missing.
    """
    res = load(required)
    if res["missing"]:
        emit('env_manager', 'validation_failed', {'missing': [m[0] for m in res["missing"]]}, level='ERROR')
        print(f"{'NAME':<25} {'DESCRIPTION':<35} {'STATUS'}")
        print("-" * 75)
        # Check all REQUIRED_VARS if required is None, otherwise just the requested ones
        all_to_show = required if required else REQUIRED_VARS.keys()
        for var in all_to_show:
            desc = REQUIRED_VARS.get(var, (None, "Unknown"))[1]
            status = "OK"
            if any(m[0] == var for m in res["missing"]):
                status = "MISSING"
            elif var in res["resolved"] and res["resolved"][var]:
                status = "OK"
            else:
                status = "MISSING"
            print(f"{var:<25} {desc:<35} {status}")
        sys.exit(1)

def _write_example():
    """Writes config/env.example if it doesn't exist."""
    if not os.path.exists(EXAMPLE_PATH):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(EXAMPLE_PATH, "w") as f:
            f.write("# Jarvis Environment Variables Example\n")
            f.write("# Copy this to .env and fill in the secrets.\n\n")
            for var, (default, desc) in REQUIRED_VARS.items():
                f.write(f"# {desc}\n")
                f.write(f"{var}={default if default else ''}\n\n")

if __name__ == "__main__":
    _write_example()
    # If running as main, validate all
    validate_or_exit()
    print("Environment validated successfully.")
