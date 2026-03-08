import os
import json
import subprocess
from pathlib import Path
import time

def run_jarvis(cmd_args, cwd=None):
    jarvis_bin = Path(__file__).parent.parent / "jarvis.py"
    venv_python = Path(__file__).parent.parent / ".venv" / "bin" / "python"
    if not venv_python.exists():
        venv_python = "python3"
    cmd = [str(venv_python), str(jarvis_bin)] + cmd_args
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).parent.parent)}
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, env=env)
    return result

def test_logger_and_cli_log(tmp_path):
    # Setup JARVIS_ROOT to tmp_path for isolated logs
    jarvis_root = tmp_path
    os.environ["JARVIS_ROOT"] = str(jarvis_root)
    
    # Import logger after setting env
    from lib.logger import get_logger
    logger = get_logger("test_comp")
    logger.info("Test message 123")
    
    log_file = jarvis_root / "logs" / "system.jsonl"
    assert log_file.exists()
    
    # Test jarvis log show
    # We need to make sure jarvis.py uses the same JARVIS_ROOT
    res = run_jarvis(["log", "show", "--lines", "1"], cwd=jarvis_root)
    assert res.returncode == 0
    assert "Test message 123" in res.stdout
    assert "test_comp" in res.stdout
