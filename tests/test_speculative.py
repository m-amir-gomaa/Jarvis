#!/usr/bin/env python3
"""
tests/test_speculative.py

Test suite for:
- pipelines/speculative_refactor.py (Sandbox Pattern)
- services/self_healer.py (_attempt_snapshot_rollback)
- pipelines/hallucination_monitor.py (Log-Driven Detection)
"""

import json
import os
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from pipelines.speculative_refactor import run_speculative
from pipelines.hallucination_monitor import detect_hallucinations
from lib.snapshot_manager import SnapshotManager


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_vault(tmp_path):
    """Create a minimal vault structure in a temp directory."""
    (tmp_path / "pipelines").mkdir()
    (tmp_path / "services").mkdir()
    (tmp_path / "logs").mkdir()
    (tmp_path / "snapshots").mkdir()
    # Seed a dummy file so the vault has content
    (tmp_path / "data.txt").write_text("original content")
    return tmp_path


@pytest.fixture()
def system_log(tmp_path):
    """Return the path for a temp system.jsonl log."""
    return tmp_path / "system.jsonl"


# ──────────────────────────────────────────────────────────────────────────────
# 1a. Sandbox Pattern (Speculative Refactor)
# ──────────────────────────────────────────────────────────────────────────────

class TestSpeculativeRefactor:
    def test_success_no_rollback(self, tmp_vault):
        """On success, changes persist and no rollback is triggered."""
        target_file = tmp_vault / "data.txt"

        def refactor():
            target_file.write_text("new content")
            return True

        with patch("pipelines.speculative_refactor.emit"):
            result = run_speculative("test_success", refactor, vault_root=tmp_vault)

        assert result is True
        assert target_file.read_text() == "new content"

    def test_failure_triggers_rollback(self, tmp_vault):
        """On test failure the snapshot is restored and old content returns."""
        target_file = tmp_vault / "data.txt"
        original_content = target_file.read_text()

        def refactor():
            target_file.write_text("broken content")
            return True  # refactor itself succeeds, but tests will fail

        with patch("pipelines.speculative_refactor.emit"), \
             patch("pipelines.speculative_refactor.subprocess.run") as mock_sub:
            mock_sub.return_value = MagicMock(returncode=1, stdout="FAILED", stderr="")
            result = run_speculative(
                "test_failure", refactor, test_cmd="pytest", vault_root=tmp_vault
            )

        assert result is False
        # After rollback the file should be back to original
        assert target_file.read_text() == original_content

    def test_refactor_func_returning_false_triggers_rollback(self, tmp_vault):
        """If the refactor callback itself returns False, rollback happens."""
        target_file = tmp_vault / "data.txt"
        original_content = target_file.read_text()

        def bad_refactor():
            target_file.write_text("halfway written")
            return False

        with patch("pipelines.speculative_refactor.emit"):
            result = run_speculative("test_bad_refactor", bad_refactor, vault_root=tmp_vault)

        assert result is False
        assert target_file.read_text() == original_content

    def test_snapshot_created_and_cleaned_on_success(self, tmp_vault):
        """Verify that a snapshot is created during a speculative run."""
        sm = SnapshotManager(tmp_vault)
        initial_count = len(sm.list_snapshots())

        with patch("pipelines.speculative_refactor.emit"):
            run_speculative("test_snapshot", lambda: True, vault_root=tmp_vault)

        final_count = len(sm.list_snapshots())
        # A snapshot should have been created (and kept)
        assert final_count > initial_count


# ──────────────────────────────────────────────────────────────────────────────
# 1b. Auto-Rollback on Self-Healer Detection
# ──────────────────────────────────────────────────────────────────────────────

class TestSelfHealerRollback:
    def test_rollback_called_when_crash_loop_detected(self, tmp_vault):
        """When a service hits restart limit, _attempt_snapshot_rollback is invoked."""
        # Create a real snapshot so there is something to roll back to
        sm = SnapshotManager(tmp_vault)
        sm.create_snapshot(label="stable")

        with patch("services.self_healer.BASE_DIR", tmp_vault), \
             patch("services.self_healer.emit"), \
             patch("services.self_healer.RESTART_HISTORY", {}):

            from services import self_healer
            # Pre-fill history to exceed limit
            from datetime import datetime, timedelta
            now = datetime.now()
            self_healer.RESTART_HISTORY["test.service"] = [
                now - timedelta(minutes=i) for i in range(self_healer.MAX_RESTARTS_PER_HOUR)
            ]
            result = self_healer.restart_service("test.service")

        assert result is False  # restart blocked, critical path triggered

    def test_rollback_no_snapshot_gracefully_fails(self, tmp_vault):
        """When no snapshots exist, rollback reports failure without crashing."""
        # Ensure no snapshots
        snap_dir = tmp_vault / "snapshots"
        for f in snap_dir.glob("*.tar.gz"):
            f.unlink()

        with patch("services.self_healer.BASE_DIR", tmp_vault), \
             patch("services.self_healer.emit") as mock_emit:
            from services import self_healer
            result = self_healer._attempt_snapshot_rollback("test.service")

        assert result is False
        mock_emit.assert_called_with(
            "self_healer", "rollback_failed",
            {"service": "test.service", "reason": "no_snapshots"}
        )

    def test_rollback_success_emits_correct_event(self, tmp_vault):
        """A successful rollback emits the rollback_success event."""
        sm = SnapshotManager(tmp_vault)
        snap = sm.create_snapshot(label="stable")

        with patch("services.self_healer.BASE_DIR", tmp_vault), \
             patch("services.self_healer.emit") as mock_emit:
            from services import self_healer
            result = self_healer._attempt_snapshot_rollback("test.service")

        assert result is True
        event_names = [c[0][1] for c in mock_emit.call_args_list]
        assert "rollback_success" in event_names


# ──────────────────────────────────────────────────────────────────────────────
# 1c. Log-Driven Hallucination Detection
# ──────────────────────────────────────────────────────────────────────────────

class TestHallucinationMonitor:
    def _write_log(self, path: Path, events: list):
        with open(path, "w") as f:
            for event in events:
                f.write(json.dumps(event) + "\n")

    def test_no_hallucination_in_clean_log(self, system_log):
        """A log with no /fix failures produces no flags."""
        self._write_log(system_log, [
            {"action": "/fix", "status": "success", "error": None},
            {"action": "/query", "status": "failure", "error": "timeout"},
        ])
        with patch("pipelines.hallucination_monitor.emit"):
            result = detect_hallucinations(log_path=system_log, threshold=3)
        assert result == []

    def test_repeated_failures_detected(self, system_log):
        """Three identical /fix failures should trigger a flag."""
        fix_failure = {"action": "/fix", "status": "failure", "error": "NameError: undefined"}
        self._write_log(system_log, [fix_failure] * 3)

        with patch("pipelines.hallucination_monitor.emit") as mock_emit:
            result = detect_hallucinations(log_path=system_log, threshold=3)

        assert len(result) == 1
        assert result[0]["error"] == "NameError: undefined"
        assert result[0]["count"] == 3
        mock_emit.assert_called_once_with(
            "hallucination_monitor", "flagged",
            {
                "error": "NameError: undefined",
                "count": 3,
                "recommendation": "human_review_or_ers_reroute",
            }
        )

    def test_below_threshold_not_flagged(self, system_log):
        """Two failures should not trigger a flag when threshold is 3."""
        fix_failure = {"action": "/fix", "status": "failure", "error": "ImportError: foo"}
        self._write_log(system_log, [fix_failure] * 2)

        with patch("pipelines.hallucination_monitor.emit"):
            result = detect_hallucinations(log_path=system_log, threshold=3)
        assert result == []

    def test_multiple_distinct_patterns(self, system_log):
        """Two distinct errors both exceeding threshold should both be flagged."""
        events = (
            [{"action": "/fix", "status": "failure", "error": "Error A"}] * 4
            + [{"action": "/fix", "status": "failure", "error": "Error B"}] * 3
        )
        self._write_log(system_log, events)

        with patch("pipelines.hallucination_monitor.emit"):
            result = detect_hallucinations(log_path=system_log, threshold=3)

        errors_flagged = {r["error"] for r in result}
        assert "Error A" in errors_flagged
        assert "Error B" in errors_flagged

    def test_missing_log_returns_empty(self, tmp_path):
        """A non-existent log file returns an empty list gracefully."""
        missing = tmp_path / "nonexistent.jsonl"
        with patch("pipelines.hallucination_monitor.emit"):
            result = detect_hallucinations(log_path=missing)
        assert result == []

    def test_malformed_lines_skipped(self, system_log):
        """Malformed JSONL lines are skipped without crashing."""
        with open(system_log, "w") as f:
            f.write("this is not json\n")
            f.write(json.dumps({"action": "/fix", "status": "failure", "error": "real error"}) + "\n")

        with patch("pipelines.hallucination_monitor.emit"):
            # Only 1 valid fix failure, below threshold of 3
            result = detect_hallucinations(log_path=system_log, threshold=3)
        assert result == []
