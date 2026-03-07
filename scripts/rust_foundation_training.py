import subprocess
import os
import sys
from pathlib import Path

BASE_DIR = Path("/home/qwerty/NixOSenv/Jarvis")
REPO_DIR = Path("/home/qwerty/NixOSenv/Jarvis")
VENV_PY = "/home/qwerty/NixOSenv/Jarvis/.venv/bin/python"
LEARNER = str(REPO_DIR / "pipelines" / "doc_learner.py")

def run_learn(path, layer, category):
    print(f"--- Training: {category} (Layer {layer}) ---")
    cmd = [VENV_PY, LEARNER, str(path), "--layer", str(layer), "--category", category]
    env = {**os.environ, "PYTHONPATH": str(BASE_DIR)}
    subprocess.run(cmd, env=env)

def main():
    # 1. Rust Foundations (Layer 1)
    # We create a small synthetic doc if we don't have a local one yet, 
    # or point to common rust doc URLs if the learner supports URLs.
    # For now, let's seed with core concepts.
    rust_core = BASE_DIR / "materials" / "rust_core.md"
    rust_core.parent.mkdir(parents=True, exist_ok=True)
    rust_core.write_text("""# Rust Core Foundations
- Memory Safety: Ownership, Borrowing, Lifetimes.
- Zero-cost abstractions.
- Pattern matching and Enums.
- Traits and Generics.
- Error handling with Result and Option.
""")
    run_learn(rust_core, 1, "rust_core")

    # 2. Rust Tooling (Layer 2)
    rust_docs = BASE_DIR / "materials" / "rust_tooling.md"
    rust_docs.write_text("""# Rust Tooling & Ecosystem
- Cargo: Build system and package manager.
- Crates.io: Registry for Rust packages.
- Rustup: Toolchain installer.
- Common Crates: serde, tokio, anyhow, clap.
""")
    run_learn(rust_docs, 2, "rust_docs")

    # 3. Advanced Rust (Layer 3)
    rust_theory = BASE_DIR / "materials" / "rust_theory.md"
    rust_theory.write_text("""# Advanced Rust Theory
- The Unsafe Superpowers.
- Advanced Traits: Associated Types, Default Generic Type Parameters, Fully Qualified Syntax.
- Macros: Declarative and Procedural macros.
- Pinning and Async internals.
""")
    run_learn(rust_theory, 3, "rust_theory")

    print("\n[Jarvis] Rust foundational training complete.")

if __name__ == "__main__":
    main()
