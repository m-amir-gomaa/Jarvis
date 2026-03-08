import asyncio
import os
from contextlib import AsyncExitStack
from typing import Optional, Any, List, Dict

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

class MCPClient:
    """
    A client to consume external tools from standard Model Context Protocol (MCP) servers.

    This client handles the lifecycle of an MCP session over stdio, allowing Jarvis
    to dynamically discover and call tools provided by external servers.

    Example:
        async with MCPClient("cat-server", ["--dry-run"]) as client:
            tools = await client.get_tools()
            result = await client.call_tool("echo", {"message": "hello"})
    """
    def __init__(self, command: str, args: Optional[List[str]] = None, env: Optional[Dict[str, str]] = None):
        """
        Initialize the MCP client parameters.

        :param command: The executable command to start the MCP server.
        :param args: Optional list of command-line arguments for the server.
        :param env: Optional environment variables for the server process.
        """
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
        """
        Connect to the given MCP server via stdio and initialize the session.
        This method is called automatically when using the async context manager.
        """
        initial_stdio = await self._exit_stack.enter_async_context(stdio_client(self.server_params))
        read, write = initial_stdio
        self.session = await self._exit_stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()

    async def disconnect(self):
        """
        Close the connection to the MCP server and clean up resources.
        This method is called automatically when using the async context manager.
        """
        await self._exit_stack.aclose()
        self.session = None

    async def get_tools(self) -> List[Any]:
        """
        List the tools available on the connected MCP server.

        :return: A list of tool definitions provided by the server.
        :raises RuntimeError: If the client is not connected.
        """
        if not self.session:
            raise RuntimeError("MCPClient is not connected.")
        
        response = await self.session.list_tools()
        return response.tools

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a specific tool exposed by the MCP server.

        :param name: The name of the tool to invoke.
        :param arguments: A dictionary of arguments to pass to the tool.
        :return: The result of the tool execution.
        :raises RuntimeError: If the client is not connected.
        """
        if not self.session:
            raise RuntimeError("MCPClient is not connected.")
            
        return await self.session.call_tool(name, arguments)

    # Could be wrapped in a context manager for easy lifecycle:
    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
