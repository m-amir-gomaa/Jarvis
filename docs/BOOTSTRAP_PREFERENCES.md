# BOOTSTRAP: Granular User Preferences (Phase 11)

This document outlines the implementation of granular user control via the Jarvis CLI.

## 1. Goal
Enable users to override system defaults for models, privacy, and permissions without editing source code. Ensure "Sensible Defaults" out of the box.

## 2. Architecture

### A. Persistent Store: `config/user_prefs.toml`
Create a new TOML-based preference store in the Vault for user-specific overrides.
- **Section: Models**: `default_local`, `default_cloud`, `reasoning_model`.
- **Section: Privacy**: `global_min_privacy`, `auto_flag_pii` (bool).
- **Section: Permissions**: `manual_approval_required` (list of caps).

### B. CLI Interface: `jarvis config`
- `jarvis config set <key> <value>`
- `jarvis config get <key>`
- `jarvis config list`
- `jarvis config reset` (restore sensible defaults)

### C. Permission Management: `jarvis cap`
- `jarvis cap list`: Show all capabilities and their current status (granted/denied/pending).
- `jarvis cap grant <cap> [session_id]`: Manual override to grant a capability.
- `jarvis cap revoke <cap>`: Remove a grant.

### D. Codebase/Privacy Flagging
- `jarvis index --flag <category>`: Force a specific category or privacy level on a directory.
- `jarvis query --privacy <level>`: Override auto-detection for a single session.

## 3. Sensible Defaults
- **Local Model**: `qwen3:14b-q4_K_M`
- **Cloud Model**: `claude-3-haiku`
- **Privacy**: `INTERNAL` for all `/home/` data, `PRIVATE` for `/THE_VAULT`.
- **Permissions**: `fs:exec` and `net:request` always require OOB approval.

## 4. Implementation Steps
1. Create `lib/prefs_manager.py` to handle CRUD on `user_prefs.toml`.
2. Update `jarvis.py` with `config` and `cap` subcommands.
3. Patch `lib/model_router.py` to prioritize `user_prefs.toml` over `models.toml`.
4. Patch `lib/security/grants.py` to support manual OOB grants via CLI.
5. Update `docs/USAGE.md` with the new control suite.
