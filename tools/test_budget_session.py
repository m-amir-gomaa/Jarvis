from lib.budget_controller import BudgetController
import uuid

def test_budget_session():
    bc = BudgetController()
    session_id = str(uuid.uuid4())
    
    bc.start_session(session_id)
    # Simulate adding large usage
    bc.record_usage("gpt-4o", "chat", 30000, 15000, session_id)
    
    decision = bc.check_session_tokens(session_id)
    assert not decision.allowed, "Should block exceeded session limits"
    
    bc.end_session(session_id)
    print("Success: test_budget_session passed.")

if __name__ == "__main__":
    test_budget_session()
