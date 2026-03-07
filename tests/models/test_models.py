# tests/models/test_models.py
import pytest
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from lib.models.router import ModelRouter
from lib.models.adapters.ollama import OllamaAdapter
from lib.models.adapters.anthropic import AnthropicAdapter
from lib.security.secrets import SecretsManager
from lib.security.context import SecurityContext, CapabilityGrant
from datetime import datetime, timezone

@pytest.fixture
def temp_keyring(tmp_path):
    return tmp_path / ".keyring"

@pytest.fixture
def sm(temp_keyring):
    return SecretsManager(keyring_path=temp_keyring)

def test_secrets_encryption_decryption(sm, temp_keyring):
    sm.set("test_key", "secret_value_123")
    assert sm.get("test_key") == "secret_value_123"
    
    # Reload from disk
    sm2 = SecretsManager(keyring_path=temp_keyring)
    assert sm2.get("test_key") == "secret_value_123"

@pytest.mark.asyncio
async def test_ollama_adapter_generate():
    adapter = OllamaAdapter()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": "Local AI Output"}
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        res = await adapter.generate("qwen", "Hello")
        assert res == "Local AI Output"

@pytest.mark.asyncio
async def test_anthropic_adapter_not_available_without_key(sm):
    adapter = AnthropicAdapter(sm)
    assert not adapter.is_available()
    with pytest.raises(ValueError, match="API key not found"):
        await adapter.generate("claude", "Hello")

@pytest.mark.asyncio
async def test_router_selects_correct_adapter():
    ollama = MagicMock(spec=OllamaAdapter)
    ollama.is_available.return_value = True
    ollama.generate = AsyncMock(return_value="Ollama result")
    
    anthropic = MagicMock(spec=AnthropicAdapter)
    anthropic.is_available.return_value = True
    anthropic.generate = AsyncMock(return_value="Anthropic result")
    
    router = ModelRouter(config={}, adapters={"ollama": ollama, "anthropic": anthropic})
    ctx = SecurityContext.default("cli")
    
    # Test local
    ctx.add_grant(CapabilityGrant(capability="model:local", granted_at=datetime.now(timezone.utc), expires_at=None, granted_by="test", scope="task"))
    res = await router.generate("local/qwen", "Hi", ctx=ctx)
    assert res == "Ollama result"
    
    # Test external
    ctx.add_grant(CapabilityGrant(capability="model:external", granted_at=datetime.now(timezone.utc), expires_at=None, granted_by="test", scope="task"))
    res = await router.generate("external/anthropic/claude", "Hi", ctx=ctx)
    assert res == "Anthropic result"

@pytest.mark.asyncio
async def test_router_fallback_to_local_when_external_fails():
    ollama = MagicMock(spec=OllamaAdapter)
    ollama.is_available.return_value = True
    ollama.generate = AsyncMock(return_value="Ollama Fallback")
    
    anthropic = MagicMock(spec=AnthropicAdapter)
    anthropic.is_available.return_value = False # Unavailable
    
    router = ModelRouter(config={"fallback_on_fail": True}, adapters={"ollama": ollama, "anthropic": anthropic})
    ctx = SecurityContext.default("cli")
    
    # Need model:external to even attempt the external call before fallback
    ctx.add_grant(CapabilityGrant(capability="model:external", granted_at=datetime.now(timezone.utc), expires_at=None, granted_by="test", scope="task"))
    # Also need model:local for the fallback
    ctx.add_grant(CapabilityGrant(capability="model:local", granted_at=datetime.now(timezone.utc), expires_at=None, granted_by="test", scope="task"))
    
    res = await router.generate("external/anthropic/claude", "Hi", ctx=ctx)
    assert res == "Ollama Fallback"
