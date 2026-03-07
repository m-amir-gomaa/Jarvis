#!/usr/bin/env python3
import argparse
import sys
import os
from pathlib import Path

# Add JARVIS_ROOT to sys.path to allow imports
JARVIS_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(JARVIS_ROOT))

try:
    from pipelines.agent_loop import AgentLoop
except ImportError:
    # Fallback for different execution environments
    sys.path.append(os.getcwd())
    from pipelines.agent_loop import AgentLoop

def main():
    parser = argparse.ArgumentParser(description="Jarvis Refactor Agent")
    parser.add_argument("--query", required=True, help="Refactoring goal")
    parser.add_argument("--max-steps", type=int, default=15, help="Max ReAct iterations")
    args = parser.parse_args()
    
    # Initialize AgentLoop with the 'refactor' specialized role
    agent = AgentLoop(task_name=f"refactor_{args.query[:20].strip().replace(' ', '_')}", role="refactor")
    
    # Run the loop. Refactoring benefits from deeper thinking.
    answer = agent.run(args.query, max_iterations=args.max_steps, thinking=True)
    
    print("\n--- Refactor Agent Result ---")
    print(answer)

if __name__ == "__main__":
    main()
