import asyncio
import os
from contextlib import AsyncExitStack
from typing import Optional, Any, List, Dict

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

class MCPClient:
    """
    A client to consume external tools from standard MCP servers.
    """
    def __init__(self, command: str, args: Optional[List[str]] = None, env: Optional[Dict[str, str]] = None):
        if env is None:
            env = dict(os.environ)
            
        self.server_params = StdioServerParameters(
            command=command,
            args=args or [],
            env=env
        )
        self.session: Optional[ClientSession] = None
        self._exit_stack = AsyncExitStack()

    async def connect(self):
        """Connect to the given MCP server via stdio."""
        initial_stdio = await self._exit_stack.enter_async_context(stdio_client(self.server_params))
        read, write = initial_stdio
        self.session = await self._exit_stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()

    async def disconnect(self):
        """Close the connection to the MCP server."""
        await self._exit_stack.aclose()
        self.session = None

    async def get_tools(self) -> List[Any]:
        """List the tools available on this MCP server."""
        if not self.session:
            raise RuntimeError("MCPClient is not connected.")
        
        response = await self.session.list_tools()
        return response.tools

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool exposed by the MCP server."""
        if not self.session:
            raise RuntimeError("MCPClient is not connected.")
            
        return await self.session.call_tool(name, arguments)

    # Could be wrapped in a context manager for easy lifecycle:
    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
