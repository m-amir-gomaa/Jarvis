import subprocess
import os
import sys
from pathlib import Path

REPO_DIR = Path("/home/qwerty/NixOSenv/Jarvis")
VENV_PY = "/home/qwerty/NixOSenv/Jarvis/.venv/bin/python"
LEARNER = str(REPO_DIR / "pipelines" / "doc_learner.py")
INDEXER = str(REPO_DIR / "tools" / "index_workspace.py")

def run_learn(path, layer, category):
    print(f"--- Learning: {category} (Layer {layer}) ---")
    cmd = [VENV_PY, LEARNER, str(path), "--layer", str(layer), "--category", category]
    env = {**os.environ, "PYTHONPATH": str(REPO_DIR)}
    subprocess.run(cmd, env=env)

def run_index(path, category):
    print(f"--- Indexing Codebase: {category} ---")
    # For simplicity, we use the existing indexer tool
    cmd = [VENV_PY, INDEXER, str(path), "--category", category]
    env = {**os.environ, "PYTHONPATH": str(REPO_DIR)}
    # Note: indexer currently doesn't take --layer, but we associate it with Layer 2 (Domain) in RAG
    subprocess.run(cmd, env=env)

def main():
    # 1. Nix Foundations (Layer 1)
    nix_core = REPO_DIR / "materials" / "nix_core.md"
    nix_core.parent.mkdir(parents=True, exist_ok=True)
    nix_core.write_text("""# Nix Core Foundations
- Pure Functional Language: Immutability, No side effects.
- Derivations: The building blocks of Nix.
- Nix Store: /nix/store and hashing.
- Standard Library: builtins, lib.
- NixOS Modules: config, options, imports.
""")
    run_learn(nix_core, 1, "nix_core")

    # 2. NixOSenv Codebase (Layer 2)
    run_index("/home/qwerty/NixOSenv", "nix_docs")

    # 3. Nix Theory & Flakes (Layer 3)
    nix_theory = REPO_DIR / "materials" / "nix_theory.md"
    nix_theory.write_text("""# Nix Theory & Flakes
- Flakes: hermetic, reproducible evaluation.
- Overlays and Overrides.
- Fixed-output derivations.
- Evaluation vs Realization.
""")
    run_learn(nix_theory, 3, "nix_theory")

    # 4. Lua Foundations (Layer 1)
    lua_core = REPO_DIR / "materials" / "lua_core.md"
    lua_core.write_text("""# Lua Core Foundations
- Tables: The only data structure.
- Metatables and Metamethods.
- Coroutines and First-class functions.
- Environment and Scopes.
""")
    run_learn(lua_core, 1, "lua_core")

    # 5. Neovim Codebase/Config (Layer 2)
    # Checking if .config/nvim exists
    nvim_dir = Path("/home/qwerty/.config/nvim")
    if nvim_dir.exists():
        run_index(str(nvim_dir), "lua_docs")
    else:
        print("Warning: Neovim config directory not found for indexing.")

    # 6. Neovim Architecture (Layer 3)
    lua_theory = REPO_DIR / "materials" / "lua_theory.md"
    lua_theory.write_text("""# Neovim & Lua Theory
- RPC Architecture.
- UI Events and Grid.
- LuaJIT performance.
- Treesitter and LSP foundations.
""")
    run_learn(lua_theory, 3, "lua_theory")

    print("\n[Jarvis] Nix and Lua training (The Jarvis Way) complete.")

if __name__ == "__main__":
    main()
