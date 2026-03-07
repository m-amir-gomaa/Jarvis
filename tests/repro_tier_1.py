# tests/repro_tier_1.py
from unittest.mock import patch, MagicMock
from pipelines.agent_loop import AgentLoop
from lib.llm import LLMResponse

def test_agent_loop_does_not_crash_on_usage():
    """ReAct loop must not raise AttributeError on usage tracking. (FIX-LOOP-1)"""
    mock_response = LLMResponse(
        content='{"thought":"done","action":"FINAL_ANSWER","action_input":{"answer":"42"}}',
        usage={"prompt_tokens": 10, "output_tokens": 5}
    )
    
    with patch("pipelines.agent_loop.ask", return_value=mock_response):
        with patch("lib.budget_controller.BudgetController.start_session") as mock_start:
            agent = AgentLoop(task_name="test_task")
            result = agent.run("What is 6x7?", max_iterations=1)
            
            # Verify session_id was passed to start_session (FIX-BUDGET-1)
            assert mock_start.called
            args, _ = mock_start.call_args
            assert args[0] is not None
            assert isinstance(args[0], str)
            
    assert "42" in result
    print("\nAgentLoop usage/session test: PASSED")

if __name__ == "__main__":
    test_agent_loop_does_not_crash_on_usage()
