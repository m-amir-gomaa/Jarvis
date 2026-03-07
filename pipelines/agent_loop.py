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

    def _get_next_action(self, history: List[Dict], user_prompt: str, response: Any) -> AgentAction:
        """Parse LLM response into an AgentAction."""
        try:
            # Handle LLMResponse object or raw string
            text = response.content if hasattr(response, "content") else str(response)
            
            # Strip markdown if model included it
            clean_res = text.strip()
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
            text = response.content if hasattr(response, "content") else str(response)
            print(f"Failed to parse ReAct action: {e}\nRaw output: {text}")
            return AgentAction(type="FINAL_ANSWER", thought="Parse failed", content=text)

    def run(self, user_prompt: str, max_iterations: int = 8, thinking: bool = False) -> str:
        """Run the ReAct loop."""
        emit('agent_loop', 'run_started', {'task': self.task_name})
        print(f"Jarvis ReAct Agent starting: {self.task_name}...")
        
        budget = BudgetController()
        session_id = str(uuid.uuid4())
        budget.start_session(session_id)
        
        history: List[Dict[str, Any]] = []
        for step in range(max_iterations):
            # 1. Budget check before each step
            decision = budget.check_session_tokens(session_id)
            if not decision.allowed:
                budget.end_session(session_id)
                self._save_history()
                return f"[Aborted: {decision.reason}] Partial: {history[-1]['obs'] if history else 'No progress'}"

            # 2. Build prompt and ask LLM
            print(f"  Step {step+1}: Thinking...")
            
            system = f"""{self.system_prompt}
You are a ReAct (Reason+Act) agent.
{self.episodic_context}

Available Tools:
{_build_tools_schema()}

At each step, you must respond EXACTLY with a JSON object. RAW JSON ONLY.
Format 1 (To use a tool):
{{
  "thought": "I need to search for X to figure out Y...",
  "action": "tool_name",
  "action_input": {{"arg": "val"}}
}}

Format 2 (Final Answer):
{{
  "thought": "I have found the final answer...",
  "action": "FINAL_ANSWER",
  "action_input": {{"answer": "..."}}
}}
"""
            context = f"User Request: {user_prompt}\n\nExecution History:\n"
            for h in history:
                context += f"Step {h['step']}:\nThought: {h['thought']}\nRan Tool: {h['tool']}\nObservation: {h['obs']}\n\n"
            context += "What is your next JSON action?"

            response = ask(
                prompt=context,
                system=system,
                task='reason',
                privacy=Privacy.INTERNAL,
                thinking=thinking
            )

            # FIX-LOGIC-1: Record usage
            budget.record_usage(
                model="qwen3:14b", # ideally response had this, but for bridge it's fine
                task="reason",
                prompt_tokens=response.usage["prompt_tokens"],
                output_tokens=response.usage["output_tokens"],
                session_id=session_id
            )

            # 3. Parse and Handle Action
            action = self._get_next_action(history, user_prompt, response=response)

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
            
            res = tool_execute(action.tool, action.args)
            obs = f"Success: {res.output}" if res.success else f"Error: {res.error} - Output: {res.output}"
            print(f"  <- Observation: {obs[:100]}...")

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
        return f"[Max steps reached] Best: {history[-1]['obs'] if history else 'None'}"

def main():
    parser = argparse.ArgumentParser(description="Jarvis Agent Loop (ReAct)")
    parser.add_argument("--task", required=True, help="Unique name for this task session")
    parser.add_argument("--user-prompt", help="Initial prompt")
    parser.add_argument("--prompt-file", help="Path to prompt file")
    parser.add_argument("--system", help="Override system prompt")
    parser.add_argument("--role", help="Expert role (e.g. 'coding')")
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument("--thinking", action="store_true")
    parser.add_argument("--output", help="Path to save answer")
    
    args = parser.parse_args()
    user_prompt = args.user_prompt
    if args.prompt_file and os.path.exists(args.prompt_file):
        with open(args.prompt_file, "r") as f:
            user_prompt = f.read()
            
    if not user_prompt:
        parser.error("Prompt required")
    
    agent = AgentLoop(args.task, system_prompt=args.system, role=args.role)
    answer = agent.run(user_prompt, max_iterations=args.max_steps, thinking=args.thinking)
    
    if args.output:
        with open(args.output, "w") as f:
            f.write(answer)
    print(f"\n--- Jarvis Response ---\n{answer}")

if __name__ == "__main__":
    main()
