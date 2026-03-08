import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from lib.mcp_client import MCPServerConfig, MCPTool, MCPHub
from lib.ers.schema import ReasoningChain, ReasoningStep, MCPToolRef
from lib.ers.augmentor import ChainAugmentor
from lib.security.context import SecurityContext

# 1. Test MCPServerConfig parsing
def test_parse_mcp_servers_toml():
    cfg = MCPServerConfig({
        "id": "test-srv",
        "name": "Test Server",
        "type": "sse",
        "url": "http://127.0.0.1:8000/sse"
    })
    assert cfg.id == "test-srv"
    assert cfg.url == "http://127.0.0.1:8000/sse"

# 2. Mock MCPHub discovery
@pytest.mark.asyncio
async def test_mcp_hub_discovery():
    with patch('lib.mcp_client.load_server_configs') as mock_load:
        mock_load.return_value = [
            MCPServerConfig({"id": "srv1", "url": "http://srv1"})
        ]
        
        hub = MCPHub()
        
        # Mock discover_tools to return something predefined
        with patch('lib.mcp_client.discover_tools', new_callable=AsyncMock) as mock_discover:
            mock_discover.return_value = [
                MCPTool("srv1", "echo", "Echoes input", {"type": "object"})
            ]
            
            res = await hub.discover_all()
            assert "srv1" in res
            assert len(res["srv1"]) == 1
            assert res["srv1"][0].name == "echo"

# 3. Test ERS Bridge (Mocking Hub call inside Augmentor)
@pytest.mark.asyncio
async def test_ers_mcp_bridge():
    chain = ReasoningChain(
        id="test-mcp-chain",
        description="Tests MCP tool step",
        steps=[
            # MCP step that takes a Jinja2 template arg
            ReasoningStep(
                id="mcp_step",
                mcp_tool=MCPToolRef(
                    server="test-srv",
                    tool="test_tool",
                    arguments={"msg": "Hello {{ user }}"}
                ),
                output_key="mcp_result"
            )
        ]
    )
    
    # Mock hub client, model router, and security manager
    mock_router = AsyncMock()
    mock_sec = Mock()
    ctx = SecurityContext("test-agent", 3)
    
    augmentor = ChainAugmentor(mock_router, mock_sec)
    
    # We patch MCPHub where it is defined since it is imported locally inside the method
    with patch('lib.mcp_client.MCPHub') as mock_hub_cls:
        mock_hub = mock_hub_cls.return_value
        mock_hub.call = AsyncMock(return_value="tool_response_123")

        
        # Run it
        initial_ctx = {"user": "Alice"}
        result = await augmentor.run_chain(chain, ctx, initial_context=initial_ctx)
        
        # Verify success and output
        assert result.success is True
        assert result.outputs.get("mcp_result") == "tool_response_123"
        
        # Verify call was made with rendered argument
        mock_hub.call.assert_called_once_with("test-srv", "test_tool", {"msg": "Hello Alice"})
        
        # Verify LLM was NOT called
        mock_router.generate.assert_not_called()
