# tests/test_stage_1_remediation.py
import pytest
import os
import importlib
from pathlib import Path

def test_audit_logger_uses_vault_root_env(monkeypatch, tmp_path):
    monkeypatch.setenv("VAULT_ROOT", str(tmp_path))
    import lib.security.audit as m
    importlib.reload(m)
    assert str(tmp_path) in str(m.DB_PATH)

def test_secrets_manager_uses_vault_root_env(monkeypatch, tmp_path):
    monkeypatch.setenv("VAULT_ROOT", str(tmp_path))
    import lib.security.secrets as m
    importlib.reload(m)
    assert str(tmp_path) in str(m.SECRETS_PATH)

def test_lsp_uses_env_roots(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_ROOT", str(tmp_path / "repo"))
    monkeypatch.setenv("VAULT_ROOT", str(tmp_path / "vault"))
    import services.jarvis_lsp as m
    importlib.reload(m)
    assert str(tmp_path / "repo") == str(m.REPO_ROOT)
    assert str(tmp_path / "vault") in str(m.SESSION_FILE)

def test_health_monitor_uses_jarvis_root(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_ROOT", str(tmp_path))
    import services.health_monitor as m
    importlib.reload(m)
    assert str(tmp_path) in str(m.PAUSE_FILE)

def test_git_monitor_uses_jarvis_root(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_ROOT", str(tmp_path))
    import services.git_monitor as m
    importlib.reload(m)
    # REPO_PATH is J_ROOT.parent
    assert str(tmp_path.parent) == m.REPO_PATH
    assert str(tmp_path) in m.LAST_COMMIT_PATH
