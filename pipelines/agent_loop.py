import os
import json
import argparse
import sys
from typing import List, Dict, Any, Optional
from lib.ollama_client import chat_managed
from lib.model_router import route
from lib.event_bus import emit
from lib.episodic_memory import get_session_context

# /THE_VAULT/jarvis/pipelines/agent_loop.py

class AgentLoop:
    def __init__(self, task_name: str, system_prompt: Optional[str] = None, role: Optional[str] = None):
        self.task_name = task_name
        self.messages = []
        self.history_path = f"/THE_VAULT/jarvis/logs/agent_{task_name}.json"
        self.episodic_context = get_session_context()
        
        # Expert Identity Loading
        if role:
            # Check for multiple possible prompt locations
            role_paths = [
                f"/THE_VAULT/jarvis/prompts/{role}/best.txt",
                f"/home/qwerty/NixOSenv/Jarvis/prompts/{role}/best.txt"
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
                self.system_prompt = "You are Jarvis, a helpful AI assistant."
        else:
            self.system_prompt = system_prompt or "You are Jarvis, a helpful AI assistant."

    def _save_history(self):
        with open(self.history_path, "w") as f:
            json.dump(self.messages, f, indent=2)

    def plan(self, user_prompt: str) -> List[Dict[str, Any]]:
        """Phase 1: Generate a structured plan using the 14B reasoning model."""
        planner_prompt = f"""
        {self.episodic_context}
        
        Decompose the following user request into a sequence of specialized sub-tasks.
        Request: "{user_prompt}"
        
        Return ONLY a JSON list of objects:
        [
          {{"task": "description", "expert": "coding|research|assistant", "reason": "why this step?"}}
        ]
        """
        try:
            plan_str = chat_managed(
                model_alias=route('reason'),
                messages=[{"role": "user", "content": planner_prompt}],
                system="You are the Jarvis Orchestrator. Output ONLY valid JSON."
            )
            # Basic JSON extraction
            start = plan_str.find("[")
            end = plan_str.rfind("]") + 1
            if start != -1 and end != -1:
                return json.loads(plan_str[start:end])
            return [{"task": user_prompt, "expert": "assistant", "reason": "Fallback to single step"}]
        except Exception:
            return [{"task": user_prompt, "expert": "assistant", "reason": "Planning failed"}]

    def run(self, user_prompt: str, max_iterations: int = 3, thinking: bool = False) -> str:
        """Phase 2: Orchestrate specialists based on the plan."""
        emit('agent_loop', 'run_started', {'task': self.task_name})
        print(f"Jarvis is orchestrating: {self.task_name}...")
        
        # 1. Create Plan
        plan = self.plan(user_prompt)
        print(f"  Plan: {len(plan)} steps generated.")
        
        # 2. Execute Steps
        context_history = []
        for i, step in enumerate(plan):
            task_desc = step["task"]
            expert = step["expert"]
            print(f"  Step {i+1}: [{expert}] {task_desc}")
            
            # Map expert to model_router task
            task_type = 'fix' if expert == 'coding' else ('chat' if expert == 'research' else 'chat')
            
            emit('agent_loop', 'step_started', {'task': self.task_name, 'step': i+1, 'expert': expert, 'reason': step['reason']})
            
            response = chat_managed(
                model_alias=route(task_type),
                messages=[*context_history, {"role": "user", "content": task_desc}],
                system=self.system_prompt + f"\nYour current focus is: {step['reason']}",
                thinking=thinking and (expert == 'coding' or i == 0) # Think on planning or coding
            )
            
            context_history.append({"role": "user", "content": task_desc})
            context_history.append({"role": "assistant", "content": response})
            emit('agent_loop', 'step_completed', {'task': self.task_name, 'step': i+1, 'expert': expert})

        self.messages = context_history
        self._save_history()
        emit('agent_loop', 'run_completed', {'task': self.task_name})
        return self.messages[-1]['content']

def main():
    parser = argparse.ArgumentParser(description="Jarvis Agent Loop")
    parser.add_argument("--task", required=True, help="Unique name for this task session")
    parser.add_argument("--user-prompt", help="Initial prompt for the agent")
    parser.add_argument("--prompt-file", help="Path to file containing initial prompt")
    parser.add_argument("--system", help="Override default system prompt")
    parser.add_argument("--role", help="Load expert role prompt (e.g. 'nixos', 'coding')")
    parser.add_argument("--max-retries", type=int, default=3, help="Max iterations")
    parser.add_argument("--thinking", action="store_true", help="Enable Qwen3 thinking mode")
    parser.add_argument("--output", help="Path to save the final answer")
    
    args = parser.parse_args()
    
    user_prompt = args.user_prompt
    if args.prompt_file and os.path.exists(args.prompt_file):
        with open(args.prompt_file, "r") as f:
            user_prompt = f.read()
            
    if not user_prompt:
        parser.error("Either --user-prompt or --prompt-file is required")
    
    agent = AgentLoop(args.task, system_prompt=args.system, role=args.role)
    answer = agent.run(user_prompt, max_iterations=args.max_retries, thinking=args.thinking)
    
    if args.output:
        with open(args.output, "w") as f:
            f.write(answer)
            
    print("\n--- Jarvis Response ---")
    print(answer)

if __name__ == "__main__":
    main()
