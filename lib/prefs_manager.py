import os
import tomllib
from pathlib import Path
from typing import Any, Optional, Dict

# /home/qwerty/NixOSenv/Jarvis/lib/prefs_manager.py

BASE_DIR = Path(os.environ.get("JARVIS_ROOT", Path(__file__).resolve().parent.parent))
VAULT_ROOT = Path(os.environ.get("VAULT_ROOT", "/THE_VAULT/jarvis"))
PREFS_PATH = VAULT_ROOT / "config" / "user_prefs.toml"

DEFAULT_PREFS = {
    "models": {
        "default_local": "qwen3:14b-q4_K_M",
        "default_cloud": "anthropic/claude-3-haiku",
        "reasoning_model": "qwen3:14b-q4_K_M",
    },
    "privacy": {
        "global_min_privacy": "internal",
        "auto_flag_pii": True,
    },
    "permissions": {
        "manual_approval_required": ["fs:exec", "net:request"],
    },
    "services": {
        "enabled_services": [
            "health", "git", "coding", "healer", "lsp", "voice"
        ],
        "health_monitor": {
            "ram_threshold_mb": 1024,
            "cpu_threshold_pct": 90,
            "notification_interval_sec": 300
        },
        "git_monitor": {
            "check_interval_sec": 3600
        }
    }
}

class PrefsManager:
    def __init__(self, prefs_path: Path = PREFS_PATH):
        self.prefs_path = prefs_path
        self.prefs_path.parent.mkdir(parents=True, exist_ok=True)
        self.session_path = VAULT_ROOT / "context" / "session_prefs.json"
        self.prefs = self._load()
        self.session_overrides = self._load_session()

    def _load(self) -> Dict[str, Any]:
        if not self.prefs_path.exists():
            return DEFAULT_PREFS.copy()
        try:
            with open(self.prefs_path, "rb") as f:
                return tomllib.load(f)
        except Exception as e:
            print(f"[PrefsManager] Error loading prefs: {e}")
            return DEFAULT_PREFS.copy()

    def _load_session(self) -> Dict[str, Any]:
        """Load session-based overrides from session_prefs.json."""
        if not self.session_path.exists():
            return {}
        try:
            import json
            with open(self.session_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[PrefsManager] Error loading session prefs: {e}")
            return {}

    def _dict_to_toml(self, d: Dict[str, Any], indent: int = 0) -> str:
        lines = []
        for k, v in d.items():
            if isinstance(v, dict):
                lines.append(f"{' ' * indent}[{k}]")
                lines.append(self._dict_to_toml(v, indent + 2))
            elif isinstance(v, str):
                lines.append(f"{' ' * indent}{k} = \"{v}\"")
            elif isinstance(v, bool):
                lines.append(f"{' ' * indent}{k} = {'true' if v else 'false'}")
            else:
                lines.append(f"{' ' * indent}{k} = {v}")
        return "\n".join(lines)

    def _save(self):
        try:
            # Try using the toml library if available for better formatting
            try:
                import toml
                with open(self.prefs_path, "w") as f:
                    toml.dump(self.prefs, f)
            except ImportError:
                # Simple fallback writer
                content = self._dict_to_toml(self.prefs)
                with open(self.prefs_path, "w") as f:
                    f.write(content)
        except Exception as e:
            print(f"[PrefsManager] Error saving prefs: {e}")

    def _save_session(self):
        """Save session-based overrides."""
        try:
            import json
            self.session_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.session_path, "w") as f:
                json.dump(self.session_overrides, f, indent=2)
        except Exception as e:
            print(f"[PrefsManager] Error saving session prefs: {e}")

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get a value using dot notation, checking session overrides first."""
        parts = key_path.split(".")
        
        # 1. Check session overrides
        val = self.session_overrides
        found = True
        for p in parts:
            if isinstance(val, dict) and p in val:
                val = val[p]
            else:
                found = False
                break
        if found:
            return val

        # 2. Check persistent prefs
        val = self.prefs
        for p in parts:
            if isinstance(val, dict) and p in val:
                val = val[p]
            else:
                return default
        return val

    def set(self, key_path: str, value: Any, persistent: bool = True):
        """Set a value using dot notation."""
        parts = key_path.split(".")
        
        target: Dict[str, Any] = self.prefs if persistent else self.session_overrides
        
        for i in range(len(parts) - 1):
            p = parts[i]
            if p not in target or not isinstance(target[p], dict):
                target[p] = {}
            target = target[p]
        
        # Type conversion for common values
        if isinstance(value, str):
            if value.lower() == "true": value = True
            elif value.lower() == "false": value = False
            elif value.isdigit(): value = int(value)
        
        target[parts[-1]] = value
        
        if persistent:
            self._save()
        else:
            self._save_session()

    def list_all(self) -> Dict[str, Any]:
        return self.prefs

    def reset(self):
        self.prefs = DEFAULT_PREFS.copy()
        self._save()
