import sys
from lib.budget_controller import BudgetController

def test_budget():
    bc = BudgetController()
    
    # Pre-test limits
    bc.config["per_task_limits"]["test"] = 100
    bc.config["limits"]["daily_tokens"] = 1000

    decision = bc.check_and_reserve("test", 150)
    assert not decision.allowed, "Should block on per-task limit"
    assert "per-task limit" in decision.reason

    decision = bc.check_and_reserve("test", 50)
    # Check what the actual capacity remaining is
    sum1 = bc.get_daily_summary()
    assert decision.allowed or sum1["tokens_used"] >= 1000

    print("Success: test_budget passed.")

if __name__ == "__main__":
    test_budget()
