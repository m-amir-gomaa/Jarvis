import os
from pathlib import Path
from lib.tools import execute, TOOL_REGISTRY

def test_tools():
    # Test shell_run
    res = execute("shell_run", {"command": "echo 'hello world'"})
    assert res.success is True
    assert "hello world" in res.output, f"Unexpected output: {res.output}"
    
    # Test python_eval
    res = execute("python_eval", {"code": "print(2 + 2)"})
    assert res.success is True
    assert "4" in res.output, f"Unexpected output: {res.output}"
    
    # Test file write/read/patch
    test_file = Path("/tmp/jarvis_test_file.txt")
    if test_file.exists():
        test_file.unlink()
        
    res = execute("file_write", {"path": str(test_file), "content": "Hello Universe"})
    assert res.success is True
    
    res = execute("file_read", {"path": str(test_file)})
    assert res.success is True
    assert res.output == "Hello Universe"
    
    res = execute("file_patch", {"path": str(test_file), "search": "Universe", "replace": "World"})
    assert res.success is True
    
    res = execute("file_read", {"path": str(test_file)})
    assert res.output == "Hello World"
    
    test_file.unlink()
    
    print("Success: test_tools passed.")

if __name__ == "__main__":
    test_tools()
