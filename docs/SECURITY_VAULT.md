# Capability-Based Security & Audit Layer

Jarvis v2 implements a sophisticated **Least Privilege Capability Enforcement** model. This system ensures that every action is backed by an explicit capability grant, isolated within a hierarchical trust model, and recorded in a non-repudiable audit trail.

## 1. Capability Trust Hierarchy

Security in Jarvis is not binary; it is based on a defined hierarchy of trust and fine-grained capabilities.

### Trust Levels
The `SecurityContext` defines five levels of trust:
- `UNTRUSTED` (0): Minimum access.
- `BASIC` (1): Default for new agents; allows basic chat and reading.
- `ELEVATED` (2): Allows model switching and network searches.
- `ADMIN` (3): Allows file execution and secret management.
- `SYSTEM` (4): Full system access; reserved for core daemons.

### Capability Trust Floors
Each capability has a "floor"—the minimum trust level required to even *request* the capability. For example:
- `chat:basic`: Floor 1 (BASIC)
- `ide:edit`: Floor 2 (ELEVATED)
- `fs:exec`: Floor 3 (ADMIN)
- `vcs:write`: Floor 3 (ADMIN)

### Interactive Grant Mechanism
When an agent requests a capability for which it has sufficient trust but no active grant, the **Interactive Grant** mechanism is triggered.
- **TTY Mode**: A blocking prompt is presented to the user in the terminal.
- **OOB (Out-of-Band) Mode**: If no TTY is available, a `CapabilityPending` exception is raised, and the request is stored in `security_audit.db`. The user can later approve this via `jarvis approve <id>`.

## 2. Vault Cryptography & Persistence

Jarvis manages sensitive credentials (API keys, session tokens) in a secure "Vault" located at `~/.jarvis/vault/`.

### Secrets Management
The `SecretsManager` handles the `.keyring` file using AES-256-CFB encryption.
- **Key Derivation**: The encryption key is derived from a stable machine-id (`/etc/machine-id`) and the current system user, ensuring that secrets are tied to the local hardware and OS identity.
- **Session Tokens**: Tokens are generated per session, signed, and rotated automatically to prevent long-term replay attacks.

## 3. Structured Audit Trail

Every security-relevant event—grants, denials, revocations, and pending requests—is recorded in a structured, queryable audit log.

### Schema & Correlation
The audit trail is stored in `logs/system.jsonl` (streaming) and mirrored in a SQLite database (`databases/security_audit.db`) for complex queries.

**Event Metadata**:
- `ts`: ISO-8601 timestamp.
- `agent_id`: The ID of the agent performing the action.
- `capability`: The specific capability involved.
- `action`: `granted`, `denied`, `revoked`, or `pending`.
- `audit_token`: A unique UUID4 correlated across the entire **Constraint-Based Execution Policy** lifecycle.
- `task_id`: Linked to the specific orchestrator task for end-to-end traceability.

## 4. Constraint-Based Execution Policy

Execution is governed by strict policies:
- **Isolation**: Agent clones inherit a trust ceiling from their parent but maintain independent grant lists.
- **Revocation**: Task-scoped grants are automatically flushed upon task completion or terminal session exit.
- **Persistence**: Only specific, user-approved capabilities (e.g., `model:local`) persist across sessions.
