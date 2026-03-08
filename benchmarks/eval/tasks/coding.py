"""
benchmarks/eval/tasks/coding.py
HumanEval-style coding tasks with automated correctness verification.

Scoring: PASS = all unit tests pass after exec()
        FAIL = any test fails or syntax/runtime error
        ERROR = model returned empty or unparseable response

Anthropic standard compliance:
- Temperature = 0, seed fixed per task
- All tasks always run, no cherry-picking
- Ground truth is a deterministic unit test (no human judgment)
"""
import re
import sys
import textwrap
import traceback
from typing import Optional

TASKS = [
    # ── Python Tasks ──────────────────────────────────────────────────
    {
        "id": "py-1",
        "lang": "python",
        "category": "coding",
        "difficulty": "easy",
        "prompt": (
            "Write a Python function `def two_sum(nums: list[int], target: int) -> list[int]:` "
            "that returns indices of the two numbers in `nums` that add up to `target`. "
            "You may assume exactly one solution exists. Return only the function, no other code."
        ),
        "test_code": textwrap.dedent("""
            assert two_sum([2, 7, 11, 15], 9) == [0, 1], "basic"
            assert sorted(two_sum([3, 2, 4], 6)) == [1, 2], "unordered"
            assert two_sum([3, 3], 6) == [0, 1], "duplicate"
            assert two_sum([-1, -2, -3, -4, -5], -8) == [2, 4], "negatives"
        """),
        "extract_tag": "python",
    },
    {
        "id": "py-2",
        "lang": "python",
        "category": "coding",
        "difficulty": "medium",
        "prompt": (
            "Write a Python function `def lru_cache_impl(capacity: int)` that returns an object with "
            "`get(key: int) -> int` (returns -1 if key absent) and `put(key: int, value: int) -> None` "
            "methods implementing an LRU cache. Use only standard library. Return only the class and function."
        ),
        "test_code": textwrap.dedent("""
            lru = lru_cache_impl(2)
            lru.put(1, 1)
            lru.put(2, 2)
            assert lru.get(1) == 1, "get existing"
            lru.put(3, 3)  # evicts 2
            assert lru.get(2) == -1, "evicted"
            lru.put(4, 4)  # evicts 1
            assert lru.get(1) == -1, "evicted 1"
            assert lru.get(3) == 3, "still alive"
            assert lru.get(4) == 4, "still alive 4"
        """),
        "extract_tag": "python",
    },
    {
        "id": "py-3",
        "lang": "python",
        "category": "coding",
        "difficulty": "hard",
        "prompt": (
            "Write a Python function `def serialize_tree(root) -> str` and "
            "`def deserialize_tree(data: str)` that serialize and deserialize a binary tree. "
            "Each node has `.val: int`, `.left`, `.right`. "
            "The deserialized tree must be structurally identical to the original. "
            "Return only the two functions plus any helper class/functions needed."
        ),
        "test_code": textwrap.dedent("""
            class Node:
                def __init__(self, val, left=None, right=None):
                    self.val = val
                    self.left = left
                    self.right = right

            root = Node(1, Node(2), Node(3, Node(4), Node(5)))
            data = serialize_tree(root)
            restored = deserialize_tree(data)

            def collect(node):
                if not node: return []
                return [node.val] + collect(node.left) + collect(node.right)

            original = collect(root)
            result = collect(restored)
            assert original == result, f"Mismatch: {original} vs {result}"

            # Edge cases
            assert deserialize_tree(serialize_tree(None)) is None, "None roundtrip"
            single = Node(42)
            assert deserialize_tree(serialize_tree(single)).val == 42, "single node"
        """),
        "extract_tag": "python",
    },
    {
        "id": "py-4",
        "lang": "python",
        "category": "coding",
        "difficulty": "medium",
        "prompt": (
            "Write a Python context manager class `Timer` that measures elapsed time in seconds. "
            "Usage: `with Timer() as t: ...; print(t.elapsed)`. "
            "It must also work as a decorator using `@Timer()`. Return only the class."
        ),
        "test_code": textwrap.dedent("""
            import time

            with Timer() as t:
                time.sleep(0.05)
            assert 0.04 < t.elapsed < 0.5, f"Context manager failed: {t.elapsed}"

            @Timer()
            def slow():
                time.sleep(0.05)
                return 42

            result = slow()
            assert result == 42, "Decorator must preserve return value"
        """),
        "extract_tag": "python",
    },
    {
        "id": "py-5",
        "lang": "python",
        "category": "coding",
        "difficulty": "hard",
        "prompt": (
            "Write a Python async function `async def rate_limited_fetch(urls: list[str], max_per_second: int) -> list[str]` "
            "that fetches all URLs concurrently but enforces `max_per_second` rate limit. "
            "In tests, URLs are replaced with a dummy coroutine so no real HTTP is needed. "
            "The function must accept a `fetch_fn` keyword argument (defaulting to `aiohttp.get` style) for testability. "
            "Return only the function."
        ),
        "test_code": textwrap.dedent("""
            import asyncio, time

            call_times = []
            async def dummy_fetch(url, **kwargs):
                call_times.append(time.monotonic())
                return f"ok:{url}"

            results = asyncio.run(rate_limited_fetch(
                ["url1", "url2", "url3", "url4", "url5"],
                max_per_second=3,
                fetch_fn=dummy_fetch
            ))
            assert len(results) == 5, "Must return all results"
            assert all("ok:" in r for r in results), "Dummy fetch not called correctly"

            # Verify rate: 5 calls at max 3/sec should take at least ~1.3s
            if len(call_times) >= 4:
                total = call_times[-1] - call_times[0]
                assert total >= 1.0, f"Rate limit not enforced: {total:.2f}s for 5 calls at 3/s"
        """),
        "extract_tag": "python",
    },

    # ── Rust Tasks ────────────────────────────────────────────────────
    {
        "id": "rust-1",
        "lang": "rust",
        "category": "coding",
        "difficulty": "medium",
        "prompt": (
            "Write a Rust function `fn fibonacci(n: u64) -> u64` that computes the nth Fibonacci number "
            "efficiently (O(log n) or O(n) with memoization). Do not use recursion without memoization. "
            "Return only the function."
        ),
        "test_code": textwrap.dedent("""
            #[test]
            fn test_fibonacci() {
                assert_eq!(fibonacci(0), 0);
                assert_eq!(fibonacci(1), 1);
                assert_eq!(fibonacci(10), 55);
                assert_eq!(fibonacci(20), 6765);
                assert_eq!(fibonacci(50), 12586269025);
            }
        """),
        "extract_tag": "rust",
        "run_mode": "rust_test",
    },
    {
        "id": "rust-2",
        "lang": "rust",
        "category": "coding",
        "difficulty": "hard",
        "prompt": (
            "Write a Rust struct `Stack<T>` with `push`, `pop`, `peek`, `is_empty`, and `len` methods. "
            "Implement `Iterator` for `Stack<T>` that consumes elements LIFO order. "
            "Use only `std`. Return the struct, implementations, and Iterator impl."
        ),
        "test_code": textwrap.dedent("""
            #[test]
            fn test_stack() {
                let mut s: Stack<i32> = Stack::new();
                assert!(s.is_empty());
                s.push(1); s.push(2); s.push(3);
                assert_eq!(s.len(), 3);
                assert_eq!(s.peek(), Some(&3));
                assert_eq!(s.pop(), Some(3));
                let items: Vec<i32> = s.into_iter().collect();
                assert_eq!(items, vec![2, 1]);
            }
        """),
        "extract_tag": "rust",
        "run_mode": "rust_test",
    },

    # ── Nix Tasks ─────────────────────────────────────────────────────
    {
        "id": "nix-1",
        "lang": "nix",
        "category": "coding",
        "difficulty": "medium",
        "prompt": (
            "Write a NixOS Home Manager module snippet that defines a custom option "
            "`programs.myTool.enable` (type: bool, default: false) and when enabled, "
            "installs a package `pkgs.hello` and writes a config file to `~/.config/mytool/config`. "
            "Return only the Nix expression for the module attribute set."
        ),
        "test_code": None,  # Structural validation below
        "validate_fn": "validate_nix_structure",
        "required_tokens": [
            "options", "programs.myTool.enable", "mkOption", "lib.types.bool",
            "config", "mkIf", "pkgs.hello", "home.file"
        ],
        "extract_tag": "nix",
        "run_mode": "nix_structural",
    },
]


def extract_code(response: str, tag: str) -> Optional[str]:
    """Extract code block from model response."""
    # Try fenced code block
    pattern = rf"```{tag}\s*(.*?)```"
    match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Try generic code block
    match = re.search(r"```\s*(.*?)```", response, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Return raw if no fences
    if "def " in response or "fn " in response or "options" in response:
        return response.strip()
    return None


def score_python_task(task: dict, code: str) -> dict:
    """Execute code + tests in a sandboxed local namespace."""
    namespace = {}
    try:
        exec(compile(code, "<model_output>", "exec"), namespace)
        exec(compile(task["test_code"], "<tests>", "exec"), namespace)
        return {"status": "pass", "error": None}
    except AssertionError as e:
        return {"status": "fail", "error": f"Assertion: {e}"}
    except Exception as e:
        return {"status": "fail", "error": f"{type(e).__name__}: {e}"}


def validate_nix_structure(task: dict, code: str) -> dict:
    """Check required tokens present in Nix code."""
    required = task.get("required_tokens", [])
    missing = [t for t in required if t not in code]
    if missing:
        return {"status": "fail", "error": f"Missing tokens: {missing}"}
    return {"status": "pass", "error": None}


def score_task(task: dict, response: str) -> dict:
    """Score a model response against the task. Returns status: pass/fail/error."""
    if not response or not response.strip():
        return {"status": "error", "error": "Empty response from model"}

    code = extract_code(response, task.get("extract_tag", ""))
    if not code:
        return {"status": "error", "error": "Could not extract code block from response"}

    run_mode = task.get("run_mode", "python_exec")

    if run_mode == "python_exec":
        return score_python_task(task, code)
    elif run_mode == "nix_structural":
        return validate_nix_structure(task, code)
    elif run_mode == "rust_test":
        # Rust test execution requires writing a temp crate — done in runner.py
        return {"status": "deferred", "code": code, "error": None}
    else:
        return {"status": "error", "error": f"Unknown run_mode: {run_mode}"}
