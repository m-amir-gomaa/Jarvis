# Jarvis Environment Primitives

Jarvis relies on a few key environment variables to locate its codebase, secure storage, and dependencies.

## Key Variables

### `JARVIS_ROOT`
- **Description**: The absolute path to the Jarvis repository.
- **Default**: `~/NixOSenv/Jarvis` (inferred from script location if not set).
- **Purpose**: Used to locate ERS chains, knowledge databases (relative to root if not in Vault), and service templates.

### `VAULT_ROOT`
- **Description**: The absolute path to the secure data storage (the "Vault").
- **Default**: `/THE_VAULT/jarvis`
- **Purpose**: Centralized storage for security audits, persistent capability grants, encrypted API keys, and RAG embeddings. This directory should ideally be on an encrypted partition or specialized storage.

### `PYTHONPATH`
- **Description**: Standard Python search path.
- **Requirement**: Must include `JARVIS_ROOT`.
- **Note**: The `jarvis` CLI automatically sets this for its sub-processes, but if running pipelines manually, ensure it is set.

## Example Setup

```bash
export JARVIS_ROOT=$HOME/development/Jarvis
export VAULT_ROOT=/mnt/secure/jarvis
export PYTHONPATH=$JARVIS_ROOT:$PYTHONPATH
```

## NixOS Integration
On NixOS, these variables are typically managed via the `modules/jarvis.nix` module or set in the user's shell profile.
