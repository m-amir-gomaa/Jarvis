import os
from lib.model_router import route, Privacy

def test_router():
    # 1. PRIVATE -> Local
    res = route(prompt="test", privacy=Privacy.PRIVATE)
    assert res.use_local is True, "PRIVATE must always use local"
    
    # 2. PUBLIC -> depends on grants (None = local fallback)
    res = route(prompt="test", privacy=Privacy.PUBLIC)
    assert res.use_local is True, "PUBLIC without context should fallback to local (no model:external grant)"
    
    print("Success: test_router passed.")

if __name__ == "__main__":
    test_router()
