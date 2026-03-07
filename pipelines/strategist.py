#!/usr/bin/env python3
"""
Strategist Pipeline (Phase 7.1)
/home/qwerty/NixOSenv/Jarvis/pipelines/strategist.py

Decomposes complex goals into actionable steps for Jarvis.
"""

import argparse
import json
import os
import re
import sys
import subprocess
from pathlib import Path

# Runtime paths
BASE_DIR = Path(os.environ.get("JARVIS_ROOT", Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(BASE_DIR))

try:
    from lib.ollama_client import chat_managed, OllamaError
    from lib.model_router import route
    from lib.event_bus import emit
except ImportError:
    # Fallback for direct execution if PYTHONPATH is not set
    sys.path.append(os.getcwd())
    from lib.ollama_client import chat_managed, OllamaError
    from lib.model_router import route
    from lib.event_bus import emit

PLAN_PROMPT = """You are the Jarvis Strategist. Your goal is to break down a high-level user request into a clear, actionable plan using Jarvis's built-in capabilities.

Available Actions:
- research: {{"query": "..."}} (Search web and summarize)
- ingest: {{"file": "..."}} (Add file/URL to knowledge base)
- generate_nix: {{"description": "..."}} (Create or modify NixOS configuration)
- validate_nixos: {{"path": "..."}} (Run nix flake check)
- query_knowledge: {{"query": "..."}} (Search internal knowledge base)
- knowledge_graph_query: {{"query": "..."}} (Query knowledge graph for relations)
- agent_task: {{"task": "...", "details": "..."}} (Invoke ReAct agent for complex coding/fixing)
- ask_user: {{"question": "..."}} (Clarify or request input)
- shell: {{"command": "..."}} (Run a safe shell command)

Output format:
JSON array of objects, each with "step" (int), "action" (string), and "params" (dict).
Respond ONLY with the JSON array. No preamble, no commentary.

Example:
[
  {{"step": 1, "action": "research", "params": {{"query": "how to setup tailscale on nixos"}}}},
  {{"step": 2, "action": "generate_nix", "params": {{"description": "enable tailscale service"}}}},
  {{"step": 3, "action": "validate_nixos", "params": {{"path": "/home/qwerty/NixOSenv"}}}}
]

User Goal: {goal}

Plan:"""

def decompose_goal(goal: str) -> list:
    messages = [{"role": "user", "content": PLAN_PROMPT.format(goal=goal)}]
    
    print(f"[Strategist] Decomposing goal: '{goal}'...")
    try:
        response = chat_managed(
            model_alias="reason",
            messages=messages,
            thinking=True,
            max_chars=5000
        )
        
        # Extract JSON array
        match = re.search(r'\[.*\]', response, re.DOTALL)
        if not match:
            print(f"Error: Could not parse plan from response. Raw: {response}")
            return []
            
        return json.loads(match.group(0))
    except (OllamaError, json.JSONDecodeError) as e:
        print(f"Error in strategist: {e}")
        return []

def execute_step(step: dict) -> bool:
    action = step.get("action")
    params = step.get("params", {})
    
    print(f"\n>>> Executing Step {step.get('step')}: {action}")
    
    jarvis_bin = str(BASE_DIR / "jarvis.py")
    venv_py = str(BASE_DIR / ".venv" / "bin" / "python")
    
    # Map strategist actions to jarvis commands
    # We call jarvis.py with a string that is easy to classify or matches direct commands
    if action == "research":
        cmd = [venv_py, jarvis_bin, f"research {params.get('query')}"]
    elif action == "ingest":
        cmd = [venv_py, jarvis_bin, f"add {params.get('file')}"]
    elif action == "generate_nix":
        cmd = [venv_py, jarvis_bin, f"write a nix module for {params.get('description')}"]
    elif action == "validate_nixos":
        cmd = [venv_py, jarvis_bin, "validate my nixos config"]
    elif action == "query_knowledge":
        cmd = [venv_py, jarvis_bin, f"what is {params.get('query')}"]
    elif action == "knowledge_graph_query":
        cmd = [venv_py, jarvis_bin, f"what do I know about {params.get('query')}"]
    elif action == "agent_task":
        # agent_task: "task", "details"
        task = params.get("task")
        details = params.get("details")
        cmd = [venv_py, jarvis_bin, f"agent task {task} with details: {details}"]
    elif action == "ask_user":
        print(f"\nJARVIS ASKS: {params.get('question')}")
        input("Press Enter once you have addressed this...")
        return True
    elif action == "shell":
        # Caution: restricted shell execution
        print(f"Executing shell command: {params.get('command')}")
        res = subprocess.run(params.get("command"), shell=True)
        return res.returncode == 0
    else:
        print(f"Warning: Unknown action '{action}'")
        return False
        
    # For Jarvis commands, we call jarvis.py
    print(f"Running: {' '.join(cmd)}")
    env = {**os.environ, "PYTHONPATH": str(BASE_DIR)}
    res = subprocess.run(cmd, env=env)
    return res.returncode == 0

def main():
    parser = argparse.ArgumentParser(description="Jarvis Strategist")
    parser.add_argument("goal", help="High-level goal to achieve")
    parser.add_argument("--execute", action="store_true", help="Execute the plan automatically")
    args = parser.parse_args()
    
    emit("strategist", "plan_started", {"goal": args.goal})
    
    plan = decompose_goal(args.goal)
    if not plan:
        print("Failed to generate a plan.")
        sys.exit(1)
        
    print("\nProposed Strategic Plan:")
    for step in plan:
        print(f"  {step.get('step')}. {step.get('action'):<20} | {step.get('params')}")
        
    if args.execute:
        print("\nStarting execution...")
        for step in plan:
            success = execute_step(step)
            if not success:
                print(f"Step {step.get('step')} failed. Aborting execution.")
                emit("strategist", "plan_failed", {"goal": args.goal, "step": step.get('step')})
                sys.exit(1)
        
        print("\nPlan execution completed successfully.")
        emit("strategist", "plan_completed", {"goal": args.goal, "steps": len(plan)})
    else:
        print("\nRun with --execute to perform these actions automatically.")

if __name__ == "__main__":
    main()
