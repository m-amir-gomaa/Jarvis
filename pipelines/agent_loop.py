import os
import json
import argparse
import sys
import uuid
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

from lib.llm import ask, Privacy
from lib.event_bus import emit
from lib.episodic_memory import get_session_context
from lib.budget_controller import BudgetController
from lib.tools import TOOL_REGISTRY, execute as tool_execute

# /home/qwerty/NixOSenv/Jarvis/pipelines/agent_loop.py

@dataclass
class AgentAction:
    type: str # 'TOOL' or 'FINAL_ANSWER'
    thought: str
    tool: str = ""
    args: Optional[Dict[str, Any]] = None
    content: str = ""

def _build_tools_schema() -> str:
    schema = []
    for name, tool in TOOL_REGISTRY.items():
        schema.append({
            "name": name,
            "description": tool.description,
            "parameters": tool.parameters
        })
    return json.dumps(schema, indent=2)

class AgentLoop:
    def __init__(self, task_name: str, system_prompt: Optional[str] = None, role: Optional[str] = None):
        self.task_name = task_name
        self.messages = []
        self.base_dir = Path(os.environ.get("JARVIS_ROOT", Path(__file__).resolve().parent.parent))
        self.history_path = str(self.base_dir / "logs" / f"agent_{task_name}.json")
        self.episodic_context = get_session_context()
        
        # Expert Identity Loading
        if role:
            # Check for multiple possible prompt locations
            role_paths = [
                str(self.base_dir / "prompts" / role / "best.txt")
            ]
            found = False
            for p in role_paths:
                if os.path.exists(p):
                    with open(p, "r") as f:
                        self.system_prompt = f.read().strip()
                        found = True
                        break
            if not found:
                print(f"Warning: Role prompt for '{role}' not found.")
                self.system_prompt = "You are Jarvis, a dynamic AI agent."
        else:
            self.system_prompt = system_prompt or "You are Jarvis, a dynamic AI agent."

    def _save_history(self):
        with open(self.history_path, "w") as f:
            json.dump(self.messages, f, indent=2)

    def _get_next_action(self, history: List[Dict], user_prompt: str) -> AgentAction:
        """Query LLM to generate the next reasoning step and action."""
        # Note: In production we use actual function calling on supported models (e.g. Gemini/Claude),
        # but for native Ollama Qwen3 we enforce JSON schema in prompt exactly.
        
        system = f"""{self.system_prompt}
You are a ReAct (Reason+Act) agent.
{self.episodic_context}

Available Tools:
{_build_tools_schema()}

At each step, you must respond EXACTLY with a JSON object. No markdown block wrappers, just raw JSON.
Format 1 (To use a tool):
{{
  "thought": "I need to search for X to figure out Y...",
  "action": "web_search",
  "action_input": {{"query": "X"}}
}}

Format 2 (To provide the final answer to the user):
{{
  "thought": "I have found the final answer from my observations...",
  "action": "FINAL_ANSWER",
  "action_input": {{"answer": "The final conclusion is..."}}
}}
"""
        # Build prompt from history
        context = f"User Request: {user_prompt}\n\nExecution History:\n"
        for h in history:
            context += f"Step {h['step']}:\n"
            context += f"Thought: {h['thought']}\n"
            context += f"Ran Tool: {h['tool']} with args {h['args']}\n"
            context += f"Observation: {h['obs']}\n\n"
        context += "What is your next JSON action?"

        response = ask(
            task='reason',
            privacy=Privacy.INTERNAL, # Let model_router decide if it can escalate
            messages=[{"role": "user", "content": context}],
            system=system,
            thinking=False # JSON formatting works better without reasoning tokens prepended 
        )
        
        try:
            # Strip markdown if model included it
            clean_res = response.strip()
            if clean_res.startswith("```json"):
                clean_res = clean_res[7:]
            if clean_res.startswith("```"):
                clean_res = clean_res[3:]
            if clean_res.endswith("```"):
                clean_res = clean_res[:-3]
                
            data = json.loads(clean_res.strip())
            
            thought = data.get("thought", "No thought")
            action = data.get("action", "")
            action_input = data.get("action_input", {})
            
            if action == "FINAL_ANSWER":
                ans = action_input.get("answer", str(action_input))
                return AgentAction(type="FINAL_ANSWER", thought=thought, content=ans)
            else:
                return AgentAction(type="TOOL", thought=thought, tool=action, args=action_input)
                
        except Exception as e:
            print(f"Failed to parse ReAct action: {e}\nRaw output: {response}")
            # If it fails to parse, assume it just wrote the final answer
            return AgentAction(type="FINAL_ANSWER", thought="Parse failed", content=response)

    def run(self, user_prompt: str, max_iterations: int = 8, thinking: bool = False) -> str:
        """Run the ReAct loop."""
        emit('agent_loop', 'run_started', {'task': self.task_name})
        print(f"Jarvis ReAct Agent starting: {self.task_name}...")
        
        budget = BudgetController()
        session_id = budget.start_session(str(uuid.uuid4()))
        
        history: List[Dict[str, Any]] = []
        for step in range(max_iterations):
            # 1. Budget check before each step
            decision = budget.check_session_tokens(session_id)
            if not decision.allowed:
                budget.end_session(session_id)
                self._save_history()
                return f"[Aborted: {decision.reason}] Partial: {history[-1]['obs'] if history else 'No progress'}"

            # 2. Get next action
            print(f"  Step {step+1}: Thinking...")
            action = self._get_next_action(history, user_prompt)

            # 3. Handle Final Answer
            if action.type == 'FINAL_ANSWER':
                print(f"  -> Final Answer REACHED.")
                budget.end_session(session_id)
                self.messages = history
                self._save_history()
                emit('agent_loop', 'run_completed', {'task': self.task_name})
                return action.content

            # 4. Execute tool
            print(f"  -> Thought: {action.thought}")
            print(f"  -> Tool: {action.tool} | Args: {action.args}")
            
            # (In the future, ask for user confirmation if required by the tool)
            
            res = tool_execute(action.tool, action.args)
            if res.success:
                obs = f"Success: {res.output}"
            else:
                obs = f"Error: {res.error} - Output: {res.output}"
                
            observation_snippet = obs[:100] + "..." if len(obs) > 100 else obs
            print(f"  <- Observation: {observation_snippet}")

            # 5. Log
            history.append({
                'step': step + 1,
                'thought': action.thought,
                'tool': action.tool,
                'args': action.args,
                'obs': obs
            })
            emit('agent_loop', 'step_complete', {'step': step + 1, 'tool': action.tool})
            self.messages = history

        budget.end_session(session_id)
        self._save_history()
        return f"[Max steps ({max_iterations}) reached] Best result: {history[-1]['obs'] if history else 'None'}"

def main():
    parser = argparse.ArgumentParser(description="Jarvis Agent Loop (ReAct)")
    parser.add_argument("--task", required=True, help="Unique name for this task session")
    parser.add_argument("--user-prompt", help="Initial prompt for the agent")
    parser.add_argument("--prompt-file", help="Path to file containing initial prompt")
    parser.add_argument("--system", help="Override default system prompt")
    parser.add_argument("--role", help="Load expert role prompt (e.g. 'nixos', 'coding')")
    parser.add_argument("--max-steps", type=int, default=8, help="Max ReAct iterations")
    parser.add_argument("--thinking", action="store_true", help="Enable Qwen3 thinking mode (not recommended for strict JSON)")
    parser.add_argument("--output", help="Path to save the final answer")
    
    args = parser.parse_args()
    
    user_prompt = args.user_prompt
    if args.prompt_file and os.path.exists(args.prompt_file):
        with open(args.prompt_file, "r") as f:
            user_prompt = f.read()
            
    if not user_prompt:
        parser.error("Either --user-prompt or --prompt-file is required")
    
    agent = AgentLoop(args.task, system_prompt=args.system, role=args.role)
    answer = agent.run(user_prompt, max_iterations=args.max_steps, thinking=args.thinking)
    
    if args.output:
        with open(args.output, "w") as f:
            f.write(answer)
            
    print("\n--- Jarvis Response ---")
    print(answer)

if __name__ == "__main__":
    main()
