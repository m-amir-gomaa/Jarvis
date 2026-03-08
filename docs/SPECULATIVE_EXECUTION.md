# Speculative Execution in Jarvis

Jarvis V2 introduces Speculative Execution, a feature designed to handle complex, potentially breaking operations safely. By enclosing tasks within a "sandbox" and utilizing atomic snapshots, Jarvis can perform deep refactoring and self-repair with guaranteed rollback if things go awry.

## 1. The Sandbox Pattern
The sandbox pattern is implemented via `pipelines/speculative_refactor.py`. It provides a safe environment for automated changes by:
1. **Pre-Action Snapshot**: Before making any modifications, the `SnapshotManager` creates a labeled backup of the entire Vault or workspace (e.g., `speculative_task_name`).
2. **Execution**: The target refactoring function is executed.
3. **Verification**: An optional test command is run to validate the changes.
4. **Commit or Rollback**:
   - If both execution and tests succeed, the changes are committed, and a `success` event is emitted on the event bus.
   - If the refactor fails or tests break, a `rollback_initiated` event is emitted. The `SnapshotManager` restores the pre-action snapshot, ensuring the system returns exactly to its previous healthy state.

This pattern allows Jarvis to aggressively pursue solutions without the risk of leaving the system in a broken or uncompilable state.

## 2. Automated Rollback Triggers
Rollbacks are not only manual but are integrated into Jarvis's autonomous monitoring pipelines:

### A. The Self-Healer Daemon (`services/self_healer.py`)
The Self-Healer constantly monitors critical `systemd --user` services (e.g., `jarvis-coding-agent`, `jarvis-git-monitor`).
- If a service crashes, it attempts to restart it.
- **Rollback Trigger**: If a service fails repeatedly and hits the `MAX_RESTARTS_PER_HOUR` limit (currently 3), this usually indicates a broken state introduced by a recent config or code change. The daemon emits a `critical_failure` event and automatically attempts to restore the most recent snapshot via `_attempt_snapshot_rollback()`.

### B. Hallucination Monitor (`pipelines/hallucination_monitor.py`)
This monitor parses the structured `system.jsonl` event log for signs of AI failure loops.
- **Rollback Trigger**: If Jarvis repeatedly attempts the same `/fix` action and fails with the exact same error string multiple times (threshold of 3 by default), it flags the incident as a hallucination. While it currently recommends human review or ERS reroute, it is architected to be a potential trigger for an autonomous structural rollback if the model is stuck in a bad local minimum.

## 3. Benefits
By integrating the Event Bus with the Snapshot Manager, Jarvis establishes a resilient "save point" system. Developers and orchestrating agents can initiate sweeping architectural changes confidently, knowing the system will gracefully downgrade or revert if the speculative branch fails compilation or runtime health checks.
