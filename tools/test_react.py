import json
from pipelines.agent_loop import AgentLoop, AgentAction

def test_react_parser():
    agent = AgentLoop(task_name="test_task")
    
    # Mock ask() to return tool format
    from unittest.mock import patch
    with patch('pipelines.agent_loop.ask', return_value='''```json\n{"thought": "I will search now.", "action": "web_search", "action_input": {"query": "python 3.12 release date"}}\n```'''):
        action = agent._get_next_action([], "Find python 3.12 release date")
        assert action.type == "TOOL"
        assert action.tool == "web_search"
        assert "python 3.12 release date" in action.args["query"]
        
    # Mock ask() to return final answer format
    with patch('pipelines.agent_loop.ask', return_value='''{"thought": "Done.", "action": "FINAL_ANSWER", "action_input": {"answer": "Oct 2023"}}'''):
        action = agent._get_next_action([], "What is it?")
        assert action.type == "FINAL_ANSWER"
        assert "Oct 2023" in action.content
        
    print("Success: test_react passed.")

if __name__ == "__main__":
    test_react_parser()
