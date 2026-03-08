"""
benchmarks/eval/tasks/factual.py
MMLU-style multiple-choice factual reasoning — systems/Linux/AI domain.

Scoring: PASS = model outputs the correct letter (A/B/C/D), FAIL = wrong, ERROR = unparseable.
All 30 questions always run. No subjective judgment.

Anthropic standard compliance:
- Questions have one unambiguous correct answer
- Scored by letter extraction only
- Temperature = 0
"""
import re
from typing import Optional

TASKS = [
    # ── Linux / Systems ──────────────────────────────────────────────
    {
        "id": "fact-1",
        "category": "factual",
        "difficulty": "easy",
        "domain": "linux",
        "question": "Which system call creates a new process by duplicating the calling process?",
        "choices": {"A": "exec", "B": "fork", "C": "clone", "D": "spawn"},
        "answer": "B",
    },
    {
        "id": "fact-2",
        "category": "factual",
        "difficulty": "easy",
        "domain": "linux",
        "question": "What is the purpose of the /proc filesystem in Linux?",
        "choices": {
            "A": "Store permanent process logs",
            "B": "Provide a virtual filesystem interface to kernel data structures",
            "C": "Cache recently accessed files",
            "D": "Mount removable storage devices"
        },
        "answer": "B",
    },
    {
        "id": "fact-3",
        "category": "factual",
        "difficulty": "medium",
        "domain": "linux",
        "question": "Which signal number is SIGKILL?",
        "choices": {"A": "9", "B": "15", "C": "11", "D": "2"},
        "answer": "A",
    },
    {
        "id": "fact-4",
        "category": "factual",
        "difficulty": "medium",
        "domain": "linux",
        "question": "In Linux memory management, what triggers the OOM killer?",
        "choices": {
            "A": "High CPU usage",
            "B": "Disk quota exceeded",
            "C": "System is unable to allocate memory and swap is exhausted",
            "D": "Network buffer overflow"
        },
        "answer": "C",
    },
    {
        "id": "fact-5",
        "category": "factual",
        "difficulty": "medium",
        "domain": "linux",
        "question": "What does the sticky bit (mode 1000) do on a directory?",
        "choices": {
            "A": "Prevents anyone from deleting the directory",
            "B": "Allows only the owner of a file to delete it from that directory",
            "C": "Makes the directory executable by all users",
            "D": "Enables setuid on all executables in the directory"
        },
        "answer": "B",
    },
    {
        "id": "fact-6",
        "category": "factual",
        "difficulty": "hard",
        "domain": "linux",
        "question": "Which Linux scheduling policy provides the hardest real-time guarantees?",
        "choices": {
            "A": "SCHED_OTHER",
            "B": "SCHED_BATCH",
            "C": "SCHED_FIFO",
            "D": "SCHED_IDLE"
        },
        "answer": "C",
    },
    {
        "id": "fact-7",
        "category": "factual",
        "difficulty": "medium",
        "domain": "linux",
        "question": "What is copy-on-write (COW) used for in Linux process forking?",
        "choices": {
            "A": "To immediately copy all parent memory pages to the child",
            "B": "To share memory pages between parent and child until one writes to them",
            "C": "To prevent the child from accessing parent memory",
            "D": "To synchronize file writes between processes"
        },
        "answer": "B",
    },
    {
        "id": "fact-8",
        "category": "factual",
        "difficulty": "hard",
        "domain": "linux",
        "question": "What is the purpose of cgroups (control groups) in Linux?",
        "choices": {
            "A": "Manage user group permissions on files",
            "B": "Limit, account for, and isolate resource usage of process groups",
            "C": "Control access to network interfaces",
            "D": "Group systemd services into targets"
        },
        "answer": "B",
    },
    {
        "id": "fact-9",
        "category": "factual",
        "difficulty": "easy",
        "domain": "linux",
        "question": "Which command shows real-time per-process CPU and memory usage?",
        "choices": {"A": "ps", "B": "df", "C": "top", "D": "lsof"},
        "answer": "C",
    },
    {
        "id": "fact-10",
        "category": "factual",
        "difficulty": "medium",
        "domain": "linux",
        "question": "In systemd, what does a .timer unit do?",
        "choices": {
            "A": "Throttles CPU usage for a service",
            "B": "Schedules a corresponding .service unit to run at specified times",
            "C": "Sets the timeout for a service startup",
            "D": "Monitors a service for crashes"
        },
        "answer": "B",
    },

    # ── NixOS / Nix ───────────────────────────────────────────────────
    {
        "id": "fact-11",
        "category": "factual",
        "difficulty": "easy",
        "domain": "nixos",
        "question": "What is the primary benefit of NixOS's declarative configuration?",
        "choices": {
            "A": "Faster boot times",
            "B": "Reproducible system state from a single configuration file",
            "C": "Compatibility with all Linux software",
            "D": "Native GPU driver support"
        },
        "answer": "B",
    },
    {
        "id": "fact-12",
        "category": "factual",
        "difficulty": "medium",
        "domain": "nixos",
        "question": "What does `nix-store --gc` do?",
        "choices": {
            "A": "Deletes the entire Nix store",
            "B": "Removes package sources from the internet cache",
            "C": "Garbage collects unreachable store paths from the Nix store",
            "D": "Clears the system's RAM cache"
        },
        "answer": "C",
    },
    {
        "id": "fact-13",
        "category": "factual",
        "difficulty": "medium",
        "domain": "nixos",
        "question": "What is the purpose of `lib.mkDefault` in a NixOS module?",
        "choices": {
            "A": "Makes an option mandatory",
            "B": "Sets an option with the lowest priority, easily overridden by others",
            "C": "Resets an option to the NixOS system default",
            "D": "Validates a module option at build time"
        },
        "answer": "B",
    },
    {
        "id": "fact-14",
        "category": "factual",
        "difficulty": "hard",
        "domain": "nixos",
        "question": "In Nix, what does the `builtins.derivation` function return?",
        "choices": {
            "A": "A shell script",
            "B": "A store path string",
            "C": "An attribute set representing a build recipe",
            "D": "A Nix flake lock file"
        },
        "answer": "C",
    },
    {
        "id": "fact-15",
        "category": "factual",
        "difficulty": "medium",
        "domain": "nixos",
        "question": "What does `nixos-rebuild switch` do that `nixos-rebuild boot` does not?",
        "choices": {
            "A": "Builds the new configuration",
            "B": "Activates the new configuration immediately without reboot",
            "C": "Rolls back to the previous generation",
            "D": "Updates the Nix channel"
        },
        "answer": "B",
    },

    # ── AI / ML Concepts ──────────────────────────────────────────────
    {
        "id": "fact-16",
        "category": "factual",
        "difficulty": "easy",
        "domain": "ai_ml",
        "question": "What does RAG stand for in the context of LLMs?",
        "choices": {
            "A": "Recursive Attention Generation",
            "B": "Retrieval-Augmented Generation",
            "C": "Reinforced Agent Grounding",
            "D": "Randomized Adaptive Gating"
        },
        "answer": "B",
    },
    {
        "id": "fact-17",
        "category": "factual",
        "difficulty": "medium",
        "domain": "ai_ml",
        "question": "In transformer models, what does 'temperature' control during text generation?",
        "choices": {
            "A": "Model inference speed",
            "B": "The randomness of token sampling from the probability distribution",
            "C": "The maximum context window length",
            "D": "GPU thermal throttling"
        },
        "answer": "B",
    },
    {
        "id": "fact-18",
        "category": "factual",
        "difficulty": "medium",
        "domain": "ai_ml",
        "question": "What is the primary purpose of RLHF (Reinforcement Learning from Human Feedback)?",
        "choices": {
            "A": "Speed up model inference",
            "B": "Reduce model size for deployment",
            "C": "Align model outputs with human preferences and values",
            "D": "Improve tokenizer vocabulary coverage"
        },
        "answer": "C",
    },
    {
        "id": "fact-19",
        "category": "factual",
        "difficulty": "hard",
        "domain": "ai_ml",
        "question": "What does 'quantization' do to a language model?",
        "choices": {
            "A": "Reduces the bit-width of model weights, trading accuracy for memory/speed",
            "B": "Increases the model's context window",
            "C": "Splits the model across multiple GPUs",
            "D": "Applies beam search during inference"
        },
        "answer": "A",
    },
    {
        "id": "fact-20",
        "category": "factual",
        "difficulty": "medium",
        "domain": "ai_ml",
        "question": "What is 'context window' in the context of LLMs?",
        "choices": {
            "A": "The GPU VRAM available for inference",
            "B": "The maximum number of tokens the model can attend to in a single forward pass",
            "C": "The number of layers in the transformer",
            "D": "The user's conversation history folder"
        },
        "answer": "B",
    },

    # ── Systems Programming ───────────────────────────────────────────
    {
        "id": "fact-21",
        "category": "factual",
        "difficulty": "medium",
        "domain": "systems",
        "question": "In Rust, what does the borrow checker prevent?",
        "choices": {
            "A": "Infinite loops",
            "B": "Data races and dangling references at compile time",
            "C": "Runtime panics from integer overflow",
            "D": "Stack overflows in recursive functions"
        },
        "answer": "B",
    },
    {
        "id": "fact-22",
        "category": "factual",
        "difficulty": "hard",
        "domain": "systems",
        "question": "What is the difference between epoll and select in Linux?",
        "choices": {
            "A": "select is async, epoll is synchronous",
            "B": "epoll scales O(1) with monitored fd count; select rescans the entire fd set O(n)",
            "C": "epoll only works on sockets; select works on all file descriptors",
            "D": "There is no functional difference; epoll is just a newer syntax"
        },
        "answer": "B",
    },
    {
        "id": "fact-23",
        "category": "factual",
        "difficulty": "medium",
        "domain": "systems",
        "question": "What is ASLR (Address Space Layout Randomization)?",
        "choices": {
            "A": "A memory allocator algorithm",
            "B": "A security technique that randomizes stack/heap/library addresses to make exploits harder",
            "C": "A cache eviction policy",
            "D": "A technique for compressing virtual memory"
        },
        "answer": "B",
    },
    {
        "id": "fact-24",
        "category": "factual",
        "difficulty": "easy",
        "domain": "systems",
        "question": "What does TCP guarantee that UDP does not?",
        "choices": {
            "A": "Low latency",
            "B": "Ordered, reliable, error-checked delivery of packets",
            "C": "Multicast support",
            "D": "Encryption of data in transit"
        },
        "answer": "B",
    },
    {
        "id": "fact-25",
        "category": "factual",
        "difficulty": "hard",
        "domain": "systems",
        "question": "In database systems, what does MVCC (Multi-Version Concurrency Control) enable?",
        "choices": {
            "A": "Automatic index creation",
            "B": "Readers never block writers and writers never block readers by keeping multiple data versions",
            "C": "Distributed consensus across replicas",
            "D": "Automatic failover to a backup database"
        },
        "answer": "B",
    },

    # ── Security ──────────────────────────────────────────────────────
    {
        "id": "fact-26",
        "category": "factual",
        "difficulty": "medium",
        "domain": "security",
        "question": "What is the principle of least privilege?",
        "choices": {
            "A": "Give users the minimum permissions needed to perform their task",
            "B": "Grant admin rights to all developers for convenience",
            "C": "Use the weakest encryption to maximize performance",
            "D": "Disable security checks in production for speed"
        },
        "answer": "A",
    },
    {
        "id": "fact-27",
        "category": "factual",
        "difficulty": "hard",
        "domain": "security",
        "question": "What is a side-channel attack?",
        "choices": {
            "A": "Attacking the network backbone rather than the endpoint",
            "B": "Exploiting information leaked by physical implementation (timing, power, EM) rather than algorithm flaws",
            "C": "Injecting malicious code via a secondary input field",
            "D": "Intercepting communications on a secondary network channel"
        },
        "answer": "B",
    },
    {
        "id": "fact-28",
        "category": "factual",
        "difficulty": "medium",
        "domain": "security",
        "question": "What does RBAC stand for?",
        "choices": {
            "A": "Remote Backup And Copy",
            "B": "Rule-Based Access Control",
            "C": "Role-Based Access Control",
            "D": "Recursive Binary Authorization Check"
        },
        "answer": "C",
    },
    {
        "id": "fact-29",
        "category": "factual",
        "difficulty": "easy",
        "domain": "security",
        "question": "What is the purpose of a salt in password hashing?",
        "choices": {
            "A": "To make the hash reversible",
            "B": "To speed up the hashing process",
            "C": "To ensure two identical passwords produce different hash values",
            "D": "To encrypt the hash output"
        },
        "answer": "C",
    },
    {
        "id": "fact-30",
        "category": "factual",
        "difficulty": "hard",
        "domain": "security",
        "question": "What distinguishes capability-based security from traditional ACL-based access control?",
        "choices": {
            "A": "ACLs are per-object; capabilities are unforgeable tokens held by subjects that grant specific access",
            "B": "Capabilities are slower but more secure than ACLs",
            "C": "ACLs work at the file level; capabilities work at the network level",
            "D": "There is no meaningful difference — they use the same mechanism"
        },
        "answer": "A",
    },
]

PROMPT_TEMPLATE = """\
Question: {question}

Choices:
A. {A}
B. {B}
C. {C}
D. {D}

Answer with only the letter of the correct choice (A, B, C, or D)."""


def format_prompt(task: dict) -> str:
    return PROMPT_TEMPLATE.format(
        question=task["question"],
        **task["choices"]
    )


def extract_answer(response: str) -> Optional[str]:
    """Extract the answer letter from model response."""
    if not response:
        return None
    text = response.strip()
    # Look for a standalone letter A/B/C/D at start of response
    match = re.match(r"^\s*([ABCD])\b", text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    # Look for "Answer: X" or "The answer is X"
    match = re.search(r"\b(?:answer(?:\s+is)?|choice)[:\s]+([ABCD])\b", text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    # Look for "X." or "(X)" pattern
    match = re.search(r"\(([ABCD])\)|^([ABCD])\.", text, re.IGNORECASE | re.MULTILINE)
    if match:
        return (match.group(1) or match.group(2)).upper()
    return None


def score_task(task: dict, response: str) -> dict:
    """Score a model response against the correct answer."""
    if not response or not response.strip():
        return {"status": "error", "error": "Empty response", "extracted": None, "correct": task["answer"]}

    extracted = extract_answer(response)
    if extracted is None:
        return {"status": "error", "error": "Could not extract letter", "extracted": None, "correct": task["answer"]}

    correct = task["answer"].upper()
    if extracted == correct:
        return {"status": "pass", "error": None, "extracted": extracted, "correct": correct}
    else:
        return {"status": "fail", "error": f"Expected {correct}, got {extracted}", "extracted": extracted, "correct": correct}
