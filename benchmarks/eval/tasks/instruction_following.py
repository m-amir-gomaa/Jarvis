"""
benchmarks/eval/tasks/instruction_following.py
IFEval-style instruction following tasks with automated constraint verification.

Each prompt includes an explicit, machine-checkable constraint.
Scoring: PASS = all constraints satisfied, FAIL = at least one violated, ERROR = no response.

Anthropic standard compliance:
- Constraints are verifiable programmatically (no judgment)
- All 20 tasks always run
"""
import re
from typing import Optional


TASKS = [
    # ── Format constraints ────────────────────────────────────────────
    {
        "id": "if-1",
        "category": "instruction_following",
        "difficulty": "easy",
        "prompt": "List exactly 3 benefits of using systemd user services. Use a numbered list (1., 2., 3.). No other text.",
        "constraints": [
            {"type": "bullet_count", "tag": "numbered", "count": 3},
            {"type": "no_extra_text_before_list"},
        ],
    },
    {
        "id": "if-2",
        "category": "instruction_following",
        "difficulty": "easy",
        "prompt": "Explain what a Nix flake is. Your response must be between 50 and 100 words. Do not use bullet points.",
        "constraints": [
            {"type": "word_count_range", "min": 50, "max": 100},
            {"type": "no_bullets"},
        ],
    },
    {
        "id": "if-3",
        "category": "instruction_following",
        "difficulty": "easy",
        "prompt": "Answer this in exactly one sentence: What is the difference between a process and a thread?",
        "constraints": [
            {"type": "sentence_count", "count": 1},
        ],
    },
    {
        "id": "if-4",
        "category": "instruction_following",
        "difficulty": "medium",
        "prompt": "Write a haiku about memory management. A haiku has exactly 3 lines with 5, 7, and 5 syllables respectively. Output only the haiku.",
        "constraints": [
            {"type": "line_count", "count": 3},
            {"type": "no_extra_lines"},
        ],
    },
    {
        "id": "if-5",
        "category": "instruction_following",
        "difficulty": "medium",
        "prompt": "Describe how garbage collection works in 5 bullet points. Each bullet must start with a dash (-). No introduction, no conclusion.",
        "constraints": [
            {"type": "bullet_count", "tag": "dash", "count": 5},
            {"type": "starts_with_bullet"},
        ],
    },
    {
        "id": "if-6",
        "category": "instruction_following",
        "difficulty": "medium",
        "prompt": "Give me a JSON object with exactly these keys: 'name', 'version', 'description'. No other keys. Output only the JSON.",
        "constraints": [
            {"type": "valid_json"},
            {"type": "json_exact_keys", "keys": ["name", "version", "description"]},
        ],
    },
    {
        "id": "if-7",
        "category": "instruction_following",
        "difficulty": "medium",
        "prompt": (
            "Summarize the CAP theorem in at most 3 sentences. "
            "Do not use the words 'however', 'but', or 'although'."
        ),
        "constraints": [
            {"type": "sentence_count_max", "max": 3},
            {"type": "forbidden_words", "words": ["however", "but", "although"]},
        ],
    },
    {
        "id": "if-8",
        "category": "instruction_following",
        "difficulty": "hard",
        "prompt": (
            "Explain what a monad is without using the words 'monad', 'functor', 'category', or 'bind'. "
            "Keep your response under 80 words."
        ),
        "constraints": [
            {"type": "forbidden_words", "words": ["monad", "functor", "category", "bind"]},
            {"type": "word_count_max", "max": 80},
        ],
    },
    {
        "id": "if-9",
        "category": "instruction_following",
        "difficulty": "hard",
        "prompt": (
            "Write a Python function that reverses a string. "
            "Your response must include a docstring, a type annotation on the parameter, "
            "a type annotation on the return value, and at least one comment. "
            "Return only the function."
        ),
        "constraints": [
            {"type": "contains_pattern", "pattern": r'""".*"""', "flags": re.DOTALL, "description": "docstring"},
            {"type": "contains_pattern", "pattern": r"def \w+\(.*:.*\).*->", "description": "type annotations"},
            {"type": "contains_pattern", "pattern": r"#.+", "description": "at least one comment"},
        ],
    },
    {
        "id": "if-10",
        "category": "instruction_following",
        "difficulty": "medium",
        "prompt": (
            "List 5 Linux commands for debugging network issues. "
            "Format as a markdown table with columns: Command, Purpose, Example. "
            "Use proper markdown table syntax."
        ),
        "constraints": [
            {"type": "contains_pattern", "pattern": r"\|.*\|.*\|", "description": "markdown table row"},
            {"type": "contains_pattern", "pattern": r"\|[-:]+\|", "description": "markdown table separator"},
        ],
    },
    {
        "id": "if-11",
        "category": "instruction_following",
        "difficulty": "easy",
        "prompt": "Respond with only a single word. What is the opposite of 'synchronous'?",
        "constraints": [
            {"type": "word_count_exact", "count": 1},
        ],
    },
    {
        "id": "if-12",
        "category": "instruction_following",
        "difficulty": "medium",
        "prompt": (
            "Explain what POSIX is. Your explanation must: "
            "(1) start with 'POSIX stands for', "
            "(2) mention at least one concrete example (file, socket, or thread API), "
            "(3) end with a period."
        ),
        "constraints": [
            {"type": "starts_with", "prefix": "POSIX stands for"},
            {"type": "contains_any", "options": ["file", "socket", "thread", "API"]},
            {"type": "ends_with_period"},
        ],
    },
    {
        "id": "if-13",
        "category": "instruction_following",
        "difficulty": "hard",
        "prompt": (
            "Write a shell one-liner that counts the number of Python files in the current directory recursively. "
            "Output only the shell command. No explanation."
        ),
        "constraints": [
            {"type": "line_count", "count": 1},
            {"type": "contains_any", "options": ["find", "fd", "ls", ".py", "python"]},
            {"type": "no_markdown_fences"},
        ],
    },
    {
        "id": "if-14",
        "category": "instruction_following",
        "difficulty": "medium",
        "prompt": (
            "Name exactly 4 programming languages that compile to native machine code. "
            "List them as a comma-separated list on a single line. No other text."
        ),
        "constraints": [
            {"type": "line_count", "count": 1},
            {"type": "comma_separated_count", "count": 4},
        ],
    },
    {
        "id": "if-15",
        "category": "instruction_following",
        "difficulty": "hard",
        "prompt": (
            "Write a brief explanation of the difference between TCP and UDP. "
            "Use exactly two paragraphs. Each paragraph must be at least 2 sentences."
        ),
        "constraints": [
            {"type": "paragraph_count", "count": 2},
        ],
    },
    # 5 more tasks for comprehensive coverage
    {
        "id": "if-16",
        "category": "instruction_following",
        "difficulty": "easy",
        "prompt": "What year was Linux first released? Answer with only the year, nothing else.",
        "constraints": [
            {"type": "word_count_exact", "count": 1},
            {"type": "contains_pattern", "pattern": r"^\d{4}$", "description": "4-digit year"},
        ],
    },
    {
        "id": "if-17",
        "category": "instruction_following",
        "difficulty": "medium",
        "prompt": (
            "Explain copy-on-write semantics. Your response must: "
            "use the acronym COW at least once, be fewer than 60 words, and not use bullet points."
        ),
        "constraints": [
            {"type": "contains_pattern", "pattern": r"\bCOW\b", "description": "acronym COW"},
            {"type": "word_count_max", "max": 60},
            {"type": "no_bullets"},
        ],
    },
    {
        "id": "if-18",
        "category": "instruction_following",
        "difficulty": "hard",
        "prompt": (
            "Give an example of a Python decorator that logs function calls. "
            "The code must be inside a ```python ... ``` code fence. "
            "Include the decorator definition and at least one usage example."
        ),
        "constraints": [
            {"type": "contains_pattern", "pattern": r"```python", "description": "python code fence"},
            {"type": "contains_pattern", "pattern": r"def \w+\(", "description": "function definition"},
            {"type": "contains_pattern", "pattern": r"@\w+", "description": "decorator usage"},
        ],
    },
    {
        "id": "if-19",
        "category": "instruction_following",
        "difficulty": "medium",
        "prompt": "Respond only with a valid JSON array of 3 strings, each being a Linux signal name.",
        "constraints": [
            {"type": "valid_json"},
            {"type": "json_is_list", "length": 3},
            {"type": "json_all_strings"},
        ],
    },
    {
        "id": "if-20",
        "category": "instruction_following",
        "difficulty": "hard",
        "prompt": (
            "Write the most space-efficient Python one-liner that checks if a string is a palindrome. "
            "Your response: must fit on one line, must not use `reverse` or `reversed`, "
            "must use slicing, and must return a boolean."
        ),
        "constraints": [
            {"type": "line_count", "count": 1},
            {"type": "forbidden_words", "words": ["reverse", "reversed"]},
            {"type": "contains_pattern", "pattern": r"::-1", "description": "slice reversal"},
        ],
    },
]

import json


def score_task(task: dict, response: str) -> dict:
    """Check all constraints against the model response. All must pass."""
    if not response or not response.strip():
        return {"status": "error", "error": "Empty response", "failed_constraints": []}

    text = response.strip()
    failures = []

    for constraint in task.get("constraints", []):
        ctype = constraint["type"]
        ok, reason = _check_constraint(ctype, constraint, text)
        if not ok:
            failures.append({"constraint": ctype, "reason": reason})

    if failures:
        return {"status": "fail", "error": None, "failed_constraints": failures}
    return {"status": "pass", "error": None, "failed_constraints": []}


def _check_constraint(ctype: str, c: dict, text: str):
    words = text.split()
    lines = [l for l in text.splitlines() if l.strip()]

    if ctype == "word_count_range":
        ok = c["min"] <= len(words) <= c["max"]
        return ok, f"Word count {len(words)} not in [{c['min']}, {c['max']}]"

    if ctype == "word_count_max":
        ok = len(words) <= c["max"]
        return ok, f"Word count {len(words)} exceeds max {c['max']}"

    if ctype == "word_count_exact":
        ok = len(words) == c["count"]
        return ok, f"Expected {c['count']} words, got {len(words)}"

    if ctype == "sentence_count":
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        ok = len(sentences) == c["count"]
        return ok, f"Expected {c['count']} sentences, got {len(sentences)}"

    if ctype == "sentence_count_max":
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        ok = len(sentences) <= c["max"]
        return ok, f"Expected ≤{c['max']} sentences, got {len(sentences)}"

    if ctype == "line_count":
        ok = len(lines) == c["count"]
        return ok, f"Expected {c['count']} lines, got {len(lines)}"

    if ctype == "no_extra_lines":
        ok = len(lines) <= 5  # generous allowance
        return ok, f"Too many lines: {len(lines)}"

    if ctype == "bullet_count":
        if c.get("tag") == "numbered":
            bullets = re.findall(r"^\s*\d+\.", text, re.MULTILINE)
        elif c.get("tag") == "dash":
            bullets = re.findall(r"^\s*-\s", text, re.MULTILINE)
        else:
            bullets = re.findall(r"^\s*[-*•]\s", text, re.MULTILINE)
        ok = len(bullets) == c["count"]
        return ok, f"Expected {c['count']} bullets, got {len(bullets)}"

    if ctype == "no_bullets":
        has = bool(re.search(r"^\s*[-*•]\s", text, re.MULTILINE))
        return not has, "Response contains bullet points"

    if ctype == "no_markdown_fences":
        has = "```" in text
        return not has, "Response contains markdown code fences"

    if ctype == "starts_with_bullet":
        ok = bool(re.match(r"^\s*[-*•\d]", text))
        return ok, "Response does not start with a bullet"

    if ctype == "paragraph_count":
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
        ok = len(paragraphs) == c["count"]
        return ok, f"Expected {c['count']} paragraphs, got {len(paragraphs)}"

    if ctype == "forbidden_words":
        found = [w for w in c["words"] if re.search(rf"\b{re.escape(w)}\b", text, re.IGNORECASE)]
        return len(found) == 0, f"Forbidden words found: {found}"

    if ctype == "contains_pattern":
        flags = c.get("flags", 0)
        ok = bool(re.search(c["pattern"], text, flags))
        return ok, f"Pattern not found: {c.get('description', c['pattern'])}"

    if ctype == "starts_with":
        ok = text.lower().startswith(c["prefix"].lower())
        return ok, f"Does not start with: '{c['prefix']}'"

    if ctype == "ends_with_period":
        ok = text.rstrip().endswith(".")
        return ok, "Response does not end with a period"

    if ctype == "contains_any":
        ok = any(opt.lower() in text.lower() for opt in c["options"])
        return ok, f"None of {c['options']} found in response"

    if ctype == "comma_separated_count":
        parts = [p.strip() for p in text.split(",")]
        ok = len(parts) == c["count"]
        return ok, f"Expected {c['count']} comma-separated items, got {len(parts)}"

    if ctype == "valid_json":
        try:
            json.loads(text)
            return True, ""
        except Exception as e:
            return False, f"Not valid JSON: {e}"

    if ctype == "json_exact_keys":
        try:
            obj = json.loads(text)
            ok = isinstance(obj, dict) and set(obj.keys()) == set(c["keys"])
            return ok, f"JSON keys mismatch. Expected {c['keys']}, got {list(obj.keys()) if isinstance(obj, dict) else '?'}"
        except Exception:
            return False, "Not valid JSON"

    if ctype == "json_is_list":
        try:
            obj = json.loads(text)
            ok = isinstance(obj, list) and len(obj) == c["length"]
            return ok, f"Expected JSON list of length {c['length']}"
        except Exception:
            return False, "Not valid JSON"

    if ctype == "json_all_strings":
        try:
            obj = json.loads(text)
            ok = isinstance(obj, list) and all(isinstance(x, str) for x in obj)
            return ok, "Not all elements are strings"
        except Exception:
            return False, "Not valid JSON"

    if ctype == "no_extra_text_before_list":
        first_line = text.splitlines()[0] if text.splitlines() else ""
        ok = bool(re.match(r"^\s*\d+\.", first_line))
        return ok, "Response has text before the list"

    return True, ""  # Unknown constraint type: skip
