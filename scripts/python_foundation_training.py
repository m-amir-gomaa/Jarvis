import subprocess
import os
import sys
from pathlib import Path

REPO_DIR = Path("/home/qwerty/NixOSenv/Jarvis")
VENV_PY = "/THE_VAULT/jarvis/.venv/bin/python"
LEARNER = str(REPO_DIR / "pipelines" / "doc_learner.py")

def run_learn(path, layer, category):
    print(f"--- Training: {category} (Layer {layer}) ---")
    cmd = [VENV_PY, LEARNER, str(path), "--layer", str(layer), "--category", category]
    env = {**os.environ, "PYTHONPATH": str(REPO_DIR)}
    subprocess.run(cmd, env=env)

def main():
    # 1. Python Tooling (Layer 2)
    py_docs = REPO_DIR / "materials" / "python_tooling.md"
    py_docs.parent.mkdir(parents=True, exist_ok=True)
    py_docs.write_text("""# Python Tooling & Packaging
- Pip: Package installer.
- Venv & Virtualenv: Isolated environments.
- Poetry & Hatch: Modern packaging and dependency management.
- Pytest: Testing framework.
- Ruff & Black: Linting and formatting.
""")
    run_learn(py_docs, 2, "python_docs")

    # 2. Advanced Python Theory (Layer 3)
    py_theory = REPO_DIR / "materials" / "python_theory.md"
    py_theory.write_text("""# Advanced Python Theory
- Asyncio internals: Event Loop, Tasks, Futures.
- Metaprogramming: Metaclasses and Type-level programming.
- C Extensions and Cython foundations.
- GIL (Global Interpreter Lock) and Multi-threading vs Multi-processing.
""")
    run_learn(py_theory, 3, "python_theory")

    print("\n[Jarvis] Python foundational training complete.")

if __name__ == "__main__":
    main()
