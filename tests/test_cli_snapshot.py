import os
import subprocess
from pathlib import Path

def run_jarvis(cmd_args, cwd=None):
    jarvis_bin = Path(__file__).parent.parent / "jarvis.py"
    venv_python = Path(__file__).parent.parent / ".venv" / "bin" / "python"
    if not venv_python.exists():
        venv_python = "python3"
    cmd = [str(venv_python), str(jarvis_bin)] + cmd_args
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).parent.parent)}
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, env=env)
    return result

def test_snapshot_commands(tmp_path):
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "data.txt").write_text("hello world")
    
    os.environ["VAULT_ROOT"] = str(vault_root)
    
    # Test create
    res = run_jarvis(["snapshot", "create", "test"], cwd=tmp_path)
    assert res.returncode == 0
    assert "Snapshot created" in res.stdout
    
    # Test list
    res = run_jarvis(["snapshot", "list"], cwd=tmp_path)
    assert res.returncode == 0
    assert "snapshot_test_" in res.stdout
    
    snapshot_name = None
    for line in res.stdout.splitlines():
        if "snapshot_test_" in line:
            snapshot_name = line.split()[0]
            break
    
    assert snapshot_name is not None
    
    # Modify data and restore
    (vault_root / "data.txt").write_text("corrupted")
    res = run_jarvis(["snapshot", "restore", snapshot_name], cwd=tmp_path)
    assert res.returncode == 0
    assert "Restore complete" in res.stdout
    assert (vault_root / "data.txt").read_text() == "hello world"
