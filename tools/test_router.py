import os
from lib.model_router import route, Privacy

def test_router():
    # 1. Private -> Local
    res = route("reason", privacy=Privacy.PRIVATE)
    assert res.backend == "local", "PRIVATE must always use local"
    
    # 2. Public, large context -> Cloud
    res = route("chat", privacy=Privacy.PUBLIC, context_tokens=20000)
    assert res.backend == "cloud", "PUBLIC with large context should use cloud"
    
    # 3. Path match -> Private -> Local
    jarvis_root = os.environ.get("JARVIS_ROOT", "/home/qwerty/NixOSenv/Jarvis")
    private_path = os.path.join(jarvis_root, "some_file.py")
    res = route("chat", privacy=Privacy.PUBLIC, context_tokens=20000, path=private_path)
    assert res.backend == "local", "Project path matches PRIVATE in codebases.toml, overrides PUBLIC"
    
    print("Success: test_router passed.")

if __name__ == "__main__":
    test_router()
