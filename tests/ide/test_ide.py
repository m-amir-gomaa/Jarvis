# tests/ide/test_ide.py
import pytest
import asyncio
from unittest.mock import MagicMock, patch
from services.jarvis_lsp import lsp_server, http_app
from lsprotocol.types import (
    InitializeParams, TEXT_DOCUMENT_COMPLETION,
    CompletionParams, TextDocumentIdentifier, Position,
    TEXT_DOCUMENT_CODE_ACTION, CodeActionParams
)

@pytest.fixture
def mock_lsp_client():
    client = MagicMock()
    return client

@pytest.mark.asyncio
async def test_lsp_initialize_clones_context():
    from services.jarvis_lsp import on_initialize, _clone_registry
    params = InitializeParams(
        process_id=123,
        root_uri="file:///tmp",
        capabilities=MagicMock(),
        initialization_options={"jarvis_session_token": "test-token-123"}
    )
    
    # Reset registry for test
    _clone_registry.clear()
    on_initialize(params)
    
    assert "default" in _clone_registry
    assert _clone_registry["default"].agent_id.startswith("ide-clone-")

@pytest.mark.asyncio
async def test_lsp_completion_is_incomplete():
    from services.jarvis_lsp import completions
    params = CompletionParams(
        text_document=TextDocumentIdentifier(uri="file:///test.py"),
        position=Position(line=0, character=0)
    )
    
    res = completions(params)
    assert res.is_incomplete is True
    assert len(res.items) == 0

@pytest.mark.asyncio
async def test_lsp_code_actions_returned():
    from services.jarvis_lsp import code_actions
    params = CodeActionParams(
        text_document=TextDocumentIdentifier(uri="file:///test.py"),
        range=MagicMock(),
        context=MagicMock()
    )
    
    res = code_actions(params)
    assert len(res) >= 1
    assert any(a.title == "Jarvis: Fix Error" for a in res)

def test_http_health_check():
    from fastapi.testclient import TestClient
    client = TestClient(http_app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_security_request_oob():
    from fastapi.testclient import TestClient
    client = TestClient(http_app)
    # Mock gm.request to raise CapabilityPending or return grant
    with patch("services.jarvis_lsp.gm.request") as mock_req:
        mock_req.return_value = MagicMock(granted=True)
        response = client.post("/security/request", json={
            "capability": "ide:edit",
            "reason": "testing",
            "scope": "task"
        })
        assert response.status_code == 200
        assert response.json()["granted"] is True
