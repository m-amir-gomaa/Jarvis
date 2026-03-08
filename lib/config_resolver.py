import os
from pathlib import Path
from typing import Dict, Any, Optional
import tomllib

def deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively merges dict2 into dict1. Lists are not merged, dict2 overwrites.
    """
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result

class ConfigResolver:
    """
    Resolves Jarvis configuration files, including per-project MCP configurations.
    """
    
    @staticmethod
    def find_project_root(start_path: Optional[os.PathLike] = None) -> Path:
        """Find the root of the project (where .git or .jarvis is located)."""
        current = Path(start_path or os.getcwd()).resolve()
        while current != current.parent:
            if (current / ".jarvis").is_dir() or (current / ".git").is_dir():
                return current
            current = current.parent
        # Default to current working directory if no root found
        return Path(start_path or os.getcwd()).resolve()

    @staticmethod
    def get_mcp_config(start_path: Optional[os.PathLike] = None) -> Dict[str, Any]:
        """
        Parses .jarvis/mcp.toml from the project root.
        Returns a dictionary of the configuration, or an empty dict if not found.
        """
        project_root = ConfigResolver.find_project_root(start_path)
        mcp_toml_path = project_root / ".jarvis" / "mcp.toml"
        
        if not mcp_toml_path.exists() or not mcp_toml_path.is_file():
            return {}
            
        try:
            with open(mcp_toml_path, "rb") as f:
                return tomllib.load(f)
        except Exception as e:
            print(f"[Jarvis] Error parsing {mcp_toml_path}: {e}")
            return {}

    @staticmethod
    def get_workspace_root(start_path: Optional[os.PathLike] = None) -> Optional[Path]:
        """Find the nearest directory containing .jarvis/workspace.toml"""
        current = Path(start_path or os.getcwd()).resolve()
        while current != current.parent:
            if (current / ".jarvis" / "workspace.toml").is_file():
                return current
            current = current.parent
        return None

    @staticmethod
    def get_config(start_path: Optional[os.PathLike] = None) -> Dict[str, Any]:
        """
        Resolves configuration hierarchically:
        1. Global config (~/.config/jarvis/config.toml)
        2. Workspace config (<workspace_root>/.jarvis/workspace.toml)
        3. Local config (<cwd>/.jarvis/config.toml)
        """
        cwd = Path(start_path or os.getcwd()).resolve()
        config: Dict[str, Any] = {}

        # 1. Global config
        global_config_path = Path.home() / ".config" / "jarvis" / "config.toml"
        if global_config_path.exists():
            try:
                with open(global_config_path, "rb") as f:
                    config = deep_merge(config, tomllib.load(f))
            except Exception as e:
                print(f"[Jarvis] Error parsing {global_config_path}: {e}")

        # 2. Workspace config
        workspace_root = ConfigResolver.get_workspace_root(cwd)
        if workspace_root:
            workspace_config_path = workspace_root / ".jarvis" / "workspace.toml"
            if workspace_config_path.exists():
                try:
                    with open(workspace_config_path, "rb") as f:
                        config = deep_merge(config, tomllib.load(f))
                except Exception as e:
                    print(f"[Jarvis] Error parsing {workspace_config_path}: {e}")

        # 3. Local config
        local_config_path = cwd / ".jarvis" / "config.toml"
        if local_config_path.exists():
            try:
                with open(local_config_path, "rb") as f:
                    config = deep_merge(config, tomllib.load(f))
            except Exception as e:
                print(f"[Jarvis] Error parsing {local_config_path}: {e}")

        # D2: Per-Project Aliases
        # Any 'model_aliases' in the merged config will organically override 
        # base ones because they are merged at the end from the local/workspace config.
        
        return config
