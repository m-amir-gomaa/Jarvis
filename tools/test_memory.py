import os
from lib.working_memory import WorkingMemory

def test_memory():
    wm = WorkingMemory()
    test_session = "test_123"
    
    # 1. Clear pre-existing
    wm.clear(test_session)
    
    # 2. Add turns
    wm.save_turn("user", "Hello, do you remember my name? I am Bob.", session_id=test_session)
    wm.save_turn("assistant", "Yes, you are Bob.", session_id=test_session)
    
    # 3. Load and verify
    msgs = wm.load_session(test_session)
    assert len(msgs) == 2, f"Expected 2 messages, got {len(msgs)}"
    assert msgs[0]["content"] == "Hello, do you remember my name? I am Bob."
    assert msgs[1]["content"] == "Yes, you are Bob."
    
    # 4. Context limiting
    for i in range(15):
        wm.save_turn("user", f"Message {i}", session_id=test_session)
        
    ctx = wm.get_context_messages(max_turns=10, session_id=test_session)
    assert len(ctx) == 10, f"Expected 10 context messages, got {len(ctx)}"
    
    # 5. Clean up
    wm.clear(test_session)
    final_msgs = wm.load_session(test_session)
    assert len(final_msgs) == 0, f"Expected 0 messages after clear, got {len(final_msgs)}"
    
    print("Success: test_memory passed.")

if __name__ == "__main__":
    test_memory()
