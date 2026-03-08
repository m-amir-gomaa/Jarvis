"""
benchmarks/eval/tasks/rag_accuracy.py
RAG precision and hallucination detection tasks.

Category A (10 tasks): Questions about content that IS indexed — model MUST answer correctly.
Category B (5 tasks): Questions about content NOT indexed — model must say "I don't know" or equivalent.

Scoring:
  Category A: PASS = answer contains expected keywords, FAIL = wrong/missing
  Category B: PASS = model appropriately expresses uncertainty, FAIL = hallucination (confident wrong answer)

Anthropic standard compliance:
- Ground truth is deterministic (keyword presence + hallucination classifier)
- Both precision AND hallucination rate reported separately
"""
import re
from typing import Optional

# Sentinel for "I don't know" detection
UNCERTAINTY_PHRASES = [
    "i don't know", "i do not know", "not in my knowledge",
    "not indexed", "no information", "cannot find",
    "don't have information", "not available", "unable to find",
    "no relevant", "no context", "not sure", "uncertain",
    "i'm not aware", "could not find", "not in the database",
]

# Category A: questions about content assumed to be indexed in Jarvis's own codebase
TASKS_INDEXED = [
    {
        "id": "rag-a-1",
        "category": "rag_accuracy",
        "rag_type": "indexed",
        "difficulty": "easy",
        "prompt": "Based on the indexed Jarvis codebase, what is the default Python executable path used by Jarvis?",
        "expected_keywords": [".venv", "python", "/home/qwerty/NixOSenv/Jarvis"],
        "hallucination_check": True,
    },
    {
        "id": "rag-a-2",
        "category": "rag_accuracy",
        "rag_type": "indexed",
        "difficulty": "easy",
        "prompt": "Based on the Jarvis knowledge base, how many services does Jarvis manage?",
        "expected_keywords": ["8", "eight", "health", "git", "coding", "lsp", "voice"],
        "hallucination_check": True,
    },
    {
        "id": "rag-a-3",
        "category": "rag_accuracy",
        "rag_type": "indexed",
        "difficulty": "medium",
        "prompt": "According to Jarvis's configuration, where is the Vault data stored?",
        "expected_keywords": ["/THE_VAULT", "jarvis"],
        "hallucination_check": True,
    },
    {
        "id": "rag-a-4",
        "category": "rag_accuracy",
        "rag_type": "indexed",
        "difficulty": "medium",
        "prompt": "What NixOS rebuild command does Jarvis recommend for applying service changes?",
        "expected_keywords": ["nixos-rebuild", "switch", "flake"],
        "hallucination_check": True,
    },
    {
        "id": "rag-a-5",
        "category": "rag_accuracy",
        "rag_type": "indexed",
        "difficulty": "medium",
        "prompt": "How does Jarvis detect whether it's running on NixOS?",
        "expected_keywords": ["/etc/NIXOS", "os-release", "is_nixos", "nix"],
        "hallucination_check": True,
    },
    {
        "id": "rag-a-6",
        "category": "rag_accuracy",
        "rag_type": "indexed",
        "difficulty": "medium",
        "prompt": "What is the Ollama API port used by Jarvis?",
        "expected_keywords": ["11434", "localhost", "ollama"],
        "hallucination_check": True,
    },
    {
        "id": "rag-a-7",
        "category": "rag_accuracy",
        "rag_type": "indexed",
        "difficulty": "hard",
        "prompt": "According to the Jarvis documentation, what is the difference between persistent and session-scoped config changes?",
        "expected_keywords": ["toml", "session", "persist", "--session", "prefs"],
        "hallucination_check": True,
    },
    {
        "id": "rag-a-8",
        "category": "rag_accuracy",
        "rag_type": "indexed",
        "difficulty": "hard",
        "prompt": "Based on the Jarvis docs, what are the five categories tested in its benchmark suite?",
        "expected_keywords": ["coding", "instruction", "factual", "agentic", "rag"],
        "hallucination_check": True,
    },
    {
        "id": "rag-a-9",
        "category": "rag_accuracy",
        "rag_type": "indexed",
        "difficulty": "easy",
        "prompt": "What tool does Jarvis use for Zsh command autocompletion?",
        "expected_keywords": ["_jarvis", "compdef", "zsh", "completion"],
        "hallucination_check": True,
    },
    {
        "id": "rag-a-10",
        "category": "rag_accuracy",
        "rag_type": "indexed",
        "difficulty": "medium",
        "prompt": "What command installs Jarvis systemd services on a non-NixOS system?",
        "expected_keywords": ["make install-services", "install_services", "bin/install_services.sh"],
        "hallucination_check": True,
    },
]

# Category B: questions about content NOT in the knowledge base — model must express uncertainty
TASKS_NOT_INDEXED = [
    {
        "id": "rag-b-1",
        "category": "rag_accuracy",
        "rag_type": "not_indexed",
        "difficulty": "easy",
        "prompt": "Based only on the indexed Jarvis knowledge base, what is the exact stock price of NVIDIA today?",
        "must_express_uncertainty": True,
        "hallucination_keywords": ["$", "USD", "dollars", r"\d+\.\d{2}"],
    },
    {
        "id": "rag-b-2",
        "category": "rag_accuracy",
        "rag_type": "not_indexed",
        "difficulty": "medium",
        "prompt": "According to the Jarvis knowledge base, what is the full name of the Jarvis project's author?",
        "must_express_uncertainty": True,
        "hallucination_keywords": ["Mohammed", "Ahmed", "Ali", "Ibrahim", "John", "Jane"],
    },
    {
        "id": "rag-b-3",
        "category": "rag_accuracy",
        "rag_type": "not_indexed",
        "difficulty": "hard",
        "prompt": "Based on indexed documents, what were the exact training compute FLOPs used to train qwen2.5-coder:14b?",
        "must_express_uncertainty": True,
        "hallucination_keywords": [r"\d+e\d+", "petaflops", "FLOP", "10^"],
    },
    {
        "id": "rag-b-4",
        "category": "rag_accuracy",
        "rag_type": "not_indexed",
        "difficulty": "medium",
        "prompt": "According to your knowledge base, what is the exact uptime SLA of Anthropic's API?",
        "must_express_uncertainty": True,
        "hallucination_keywords": ["99.9", "99.5", "SLA", "uptime guarantee", "%"],
    },
    {
        "id": "rag-b-5",
        "category": "rag_accuracy",
        "rag_type": "not_indexed",
        "difficulty": "hard",
        "prompt": "Based on the indexed Jarvis docs, what is the complete source code of jarvis-health-monitor.py?",
        "must_express_uncertainty": True,
        "hallucination_keywords": ["def check_health", "import threading", "class"],
    },
]

ALL_TASKS = TASKS_INDEXED + TASKS_NOT_INDEXED


def score_indexed_task(task: dict, response: str) -> dict:
    """Category A: check that expected keywords appear in the response."""
    if not response or not response.strip():
        return {"status": "error", "error": "Empty response"}

    text = response.lower()
    expected = task.get("expected_keywords", [])
    found = [kw for kw in expected if kw.lower() in text]
    missing = [kw for kw in expected if kw.lower() not in text]

    # Need at least half the expected keywords to pass
    threshold = max(1, len(expected) // 2)
    if len(found) >= threshold:
        return {"status": "pass", "error": None, "keywords_found": found, "keywords_missing": missing}
    return {
        "status": "fail",
        "error": f"Only {len(found)}/{len(expected)} expected keywords found: missing {missing}",
        "keywords_found": found,
        "keywords_missing": missing,
    }


def score_not_indexed_task(task: dict, response: str) -> dict:
    """Category B: model must express uncertainty. A confident specific answer = hallucination."""
    if not response or not response.strip():
        return {"status": "error", "error": "Empty response"}

    text = response.lower()

    # Check if the model expressed uncertainty
    expressed_uncertainty = any(phrase in text for phrase in UNCERTAINTY_PHRASES)

    # Check if it hallucinated a confident specific answer
    hallucination_patterns = task.get("hallucination_keywords", [])
    hallucinated = any(re.search(pat, response, re.IGNORECASE) for pat in hallucination_patterns)

    if expressed_uncertainty and not hallucinated:
        return {"status": "pass", "error": None, "uncertainty_expressed": True, "hallucinated": False}
    elif hallucinated:
        return {
            "status": "fail",
            "error": "Model hallucinated a specific answer for an un-indexed question",
            "uncertainty_expressed": expressed_uncertainty,
            "hallucinated": True,
        }
    else:
        # Didn't express uncertainty but also didn't obviously hallucinate — borderline
        return {
            "status": "fail",
            "error": "Model did not express appropriate uncertainty for an un-indexed question",
            "uncertainty_expressed": False,
            "hallucinated": False,
        }


def score_task(task: dict, response: str) -> dict:
    """Route to correct scorer based on rag_type."""
    if task.get("rag_type") == "indexed":
        return score_indexed_task(task, response)
    elif task.get("rag_type") == "not_indexed":
        return score_not_indexed_task(task, response)
    return {"status": "error", "error": "Unknown rag_type"}
