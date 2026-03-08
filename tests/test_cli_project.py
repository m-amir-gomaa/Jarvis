import os
import subprocess
from pathlib import Path

def run_jarvis(cmd_args, cwd=None):
    jarvis_bin = Path(__file__).parent.parent / "jarvis.py"
    venv_python = Path(__file__).parent.parent / ".venv" / "bin" / "python"
    
    # If no venv, just fallback to python3
    if not venv_python.exists():
        venv_python = "python3"
        
    cmd = [str(venv_python), str(jarvis_bin)] + cmd_args
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).parent.parent)}
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, env=env)
    return result

def test_project_init(tmp_path):
    # Test project init
    res = run_jarvis(["project", "init"], cwd=tmp_path)
    assert res.returncode == 0
    assert "Initialized project" in res.stdout
    assert (tmp_path / ".jarvis-project.toml").exists()
    
    # Test second init (should say already initialized)
    res2 = run_jarvis(["project", "init"], cwd=tmp_path)
    assert res2.returncode == 0
    assert "Project already initialized" in res2.stdout

def test_project_status(tmp_path):
    run_jarvis(["project", "init"], cwd=tmp_path)
    res = run_jarvis(["project", "status"], cwd=tmp_path)
    assert res.returncode == 0
    assert "Project Status:" in res.stdout
    assert tmp_path.name in res.stdout

def test_project_switch(tmp_path):
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    
    res = run_jarvis(["project", "switch", str(target_dir)], cwd=tmp_path)
    assert res.returncode == 0
    assert "Switched active project context to" in res.stdout
