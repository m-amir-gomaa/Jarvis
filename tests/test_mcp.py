import pytest
from pathlib import Path

from lib.config_resolver import ConfigResolver

def test_config_resolver_find_root(tmp_path):
    project_root = tmp_path / "myproject"
    project_root.mkdir()
    (project_root / ".jarvis").mkdir()
    
    sub_dir = project_root / "src" / "deep" / "dir"
    sub_dir.mkdir(parents=True)
    
    found_root = ConfigResolver.find_project_root(sub_dir)
    assert found_root == project_root.resolve()

def test_config_resolver_get_config(tmp_path):
    project_root = tmp_path / "myproject"
    project_root.mkdir()
    jarvis_dir = project_root / ".jarvis"
    jarvis_dir.mkdir()
    
    toml_content = b'name = "test_project"\n[mcp]\nserver = "local"\n'
    mcp_toml = jarvis_dir / "mcp.toml"
    with open(mcp_toml, "wb") as f:
        f.write(toml_content)
        
    config = ConfigResolver.get_mcp_config(project_root)
    assert config == {"name": "test_project", "mcp": {"server": "local"}}

def test_config_resolver_no_config(tmp_path):
    project_root = tmp_path / "myproject"
    project_root.mkdir()
    
    config = ConfigResolver.get_mcp_config(project_root)
    assert config == {}

@pytest.mark.asyncio
async def test_mcp_client_init():
    from lib.mcp_client import MCPClient
    client = MCPClient("echo", ["hello"])
    assert client.server_params.command == "echo"
    assert client.server_params.args == ["hello"]
