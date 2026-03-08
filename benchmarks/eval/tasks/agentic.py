"""
benchmarks/eval/tasks/agentic.py
Multi-step agentic tool-use tasks with log-sequence verification.

Each task describes a job that requires specific tools in a specific order.
The scorer checks the tool call log emitted by the agent, not subjective output quality.

Anthropic standard compliance:
- Ground truth = required tool sequence (order matters for some, set for others)
- PASS = all required tools called with correct arguments
- FAIL = missing tool, wrong order (when order matters), or wrong args
"""
from typing import Optional


TASKS = [
    {
        "id": "agent-1",
        "category": "agentic",
        "difficulty": "easy",
        "title": "Index and Query Codebase",
        "prompt": (
            "I need you to: 1) Index the Jarvis codebase at ~/NixOSenv/Jarvis, "
            "2) Then query it for 'how does the event bus work'. "
            "Show me the results."
        ),
        "required_tool_calls": [
            {"tool": "index_codebase", "args_contain": {"path": "Jarvis"}, "order": 1},
            {"tool": "query_knowledge", "args_contain": {"query": "event bus"}, "order": 2},
        ],
        "require_ordered": True,
    },
    {
        "id": "agent-2",
        "category": "agentic",
        "difficulty": "medium",
        "title": "Check Service Health Then Restart Degraded Service",
        "prompt": (
            "Check the health of all Jarvis services. "
            "If any are not running, restart them. "
            "Report the final status."
        ),
        "required_tool_calls": [
            {"tool": "get_service_status", "args_contain": {}, "order": 1},
            # Conditionally restart — scorer checks that status was checked BEFORE any restart
            {"tool": "restart_service", "args_contain": {}, "order": 2, "conditional": True},
        ],
        "require_ordered": True,
    },
    {
        "id": "agent-3",
        "category": "agentic",
        "difficulty": "medium",
        "title": "Research and Summarize",
        "prompt": (
            "Research the topic 'NixOS flake composability patterns' "
            "and produce a structured summary with at least 3 key insights."
        ),
        "required_tool_calls": [
            {"tool": "web_search", "args_contain": {"query": "NixOS"}, "order": 1},
            {"tool": "summarize_content", "args_contain": {}, "order": 2},
        ],
        "require_ordered": True,
        "output_constraints": [
            {"type": "min_insights", "count": 3},
        ],
    },
    {
        "id": "agent-4",
        "category": "agentic",
        "difficulty": "hard",
        "title": "Debug Service Failure With Root Cause Analysis",
        "prompt": (
            "The jarvis-coding-agent service failed. "
            "Investigate: check journalctl logs, check if port 7002 is in use, "
            "identify the root cause, and propose a fix."
        ),
        "required_tool_calls": [
            {"tool": "read_journal_logs", "args_contain": {"service": "coding"}, "order": 1},
            {"tool": "check_port", "args_contain": {"port": 7002}, "order": 2},
            # Root cause in output — verified by output_constraints
        ],
        "require_ordered": True,
        "output_constraints": [
            {"type": "contains_any", "options": ["root cause", "because", "failed due", "error"]},
            {"type": "contains_any", "options": ["fix", "solution", "restart", "kill"]},
        ],
    },
    {
        "id": "agent-5",
        "category": "agentic",
        "difficulty": "hard",
        "title": "Multi-Step Knowledge Ingestion and Validation",
        "prompt": (
            "Ingest the file at /tmp/test_doc.md into the knowledge base with category 'test_eval'. "
            "Then immediately query for content from 'test_eval' to verify it was indexed. "
            "Report whether the content is retrievable."
        ),
        "required_tool_calls": [
            {"tool": "ingest_document", "args_contain": {"path": "/tmp/test_doc.md", "category": "test_eval"}, "order": 1},
            {"tool": "query_knowledge", "args_contain": {"category": "test_eval"}, "order": 2},
        ],
        "require_ordered": True,
        "output_constraints": [
            {"type": "contains_any", "options": ["retrievable", "found", "indexed", "successfully"]},
        ],
    },
]


def score_task(task: dict, tool_log: list, final_output: str) -> dict:
    """
    Score an agentic task given the tool call log and final output.
    tool_log: list of dicts like {"tool": str, "args": dict, "timestamp": float}
    """
    if not tool_log and not final_output:
        return {"status": "error", "error": "No tool calls and no output recorded"}

    failures = []
    required = task.get("required_tool_calls", [])

    if task.get("require_ordered"):
        # Build ordered sequence of tool names actually called
        actual_sequence = [entry.get("tool", "") for entry in tool_log]

        # Check each required tool in order
        last_found_idx: int = -1
        for req in sorted(required, key=lambda r: r.get("order", 0)):
            tool_name = req["tool"]
            conditional = req.get("conditional", False)

            found_idx: Optional[int] = None
            for i, entry in enumerate(tool_log):
                if entry.get("tool") == tool_name and i > last_found_idx:
                    # Check args_contain
                    args = entry.get("args", {})
                    args_match = all(
                        str(v).lower() in str(args.get(k, "")).lower()
                        for k, v in req.get("args_contain", {}).items()
                    )
                    if args_match:
                        found_idx = i
                        break

            if found_idx is None:
                if not conditional:
                    failures.append(f"Required tool '{tool_name}' not called in order (after step {req.get('order', '?') - 1})")
            else:
                assert found_idx is not None
                last_found_idx = found_idx
    else:
        # Unordered: just check presence
        actual_tools = {entry.get("tool") for entry in tool_log}
        for req in required:
            if req["tool"] not in actual_tools and not req.get("conditional", False):
                failures.append(f"Required tool '{req['tool']}' not called")

    # Check output constraints
    output = final_output or ""
    for con in task.get("output_constraints", []):
        if con["type"] == "contains_any":
            if not any(opt.lower() in output.lower() for opt in con["options"]):
                failures.append(f"Output missing required content — expected one of {con['options']}")
        elif con["type"] == "min_insights":
            # Count numbered items or bullet points
            import re
            count = len(re.findall(r"(?:^|\n)\s*(?:\d+[.)]|[-*•])\s", output))
            if count < con["count"]:
                failures.append(f"Expected at least {con['count']} structured insights, found {count}")

    if failures:
        return {"status": "fail", "error": "; ".join(failures)}
    return {"status": "pass", "error": None}
