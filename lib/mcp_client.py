# lib/mcp_client.py
"""
MCP Client & Hub for Jarvis Tool Hub (feature/mcp-hub)

Provides:
  - MCPClient     : stdio-based session (original implementation, unchanged)
  - MCPServerConfig: parsed definition of a server from mcp_servers.toml
  - MCPTool       : a tool discovered from a remote server
  - load_server_configs(): reads config/mcp_servers.toml
  - discover_tools()    : queries a single SSE server's tool list
  - call_mcp_tool()     : invokes a tool on a single SSE server
  - MCPHub              : top-level facade used by ERS chains and CLI
"""
from __future__ import annotations

import asyncio
import logging
import os
import tomllib
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

log = logging.getLogger("jarvis.mcp_client")

# ── Original stdio client (unchanged) ─────────────────────────────────────────

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

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()


# ── MCP Hub: server config, discovery, SSE tool calls ─────────────────────────

class MCPServerConfig:
    """Parsed definition of a single MCP server from mcp_servers.toml."""

    def __init__(self, cfg: dict):
        self.id: str = cfg["id"]
        self.name: str = cfg.get("name", self.id)
        self.type: str = cfg.get("type", "sse")
        self.url: str = cfg.get("url", "")
        self.command: str = cfg.get("command", "")
        self.enabled: bool = cfg.get("enabled", True)

    def __repr__(self) -> str:
        return f"MCPServerConfig(id={self.id!r}, type={self.type!r}, url={self.url!r})"


class MCPTool:
    """Describes a single tool discovered from an MCP server."""

    def __init__(self, server_id: str, name: str, description: str, input_schema: dict):
        self.server_id = server_id
        self.name = name
        self.description = description
        self.input_schema = input_schema

    def __repr__(self) -> str:
        return f"MCPTool(server={self.server_id!r}, name={self.name!r})"


def load_server_configs(config_path: Path | str | None = None) -> list[MCPServerConfig]:
    """Load all enabled server configs from config/mcp_servers.toml."""
    if config_path is None:
        root = Path(os.environ.get("JARVIS_ROOT", Path(__file__).resolve().parent.parent))
        config_path = root / "config" / "mcp_servers.toml"
    config_path = Path(config_path)

    if not config_path.exists():
        log.warning(f"MCP server config not found at {config_path}")
        return []

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    servers = []
    for raw in data.get("servers", []):
        try:
            cfg = MCPServerConfig(raw)
            if cfg.enabled:
                servers.append(cfg)
        except Exception as e:
            log.warning(f"Skipping invalid server config: {e}")

    return servers


async def discover_tools(server: MCPServerConfig, timeout: float = 5.0) -> list[MCPTool]:
    """
    Connect to an SSE MCP server and retrieve its tool list.
    Returns a list of MCPTool objects; logs and returns [] on any failure.
    """
    tools: list[MCPTool] = []
    try:
        from mcp.client.sse import sse_client
    except ImportError:
        log.error("mcp[sse] not available. Run: pip install 'mcp[cli]'")
        return []

    try:
        async with sse_client(server.url) as (read, write):
            async with ClientSession(read, write) as session:
                await asyncio.wait_for(session.initialize(), timeout=timeout)
                result = await asyncio.wait_for(session.list_tools(), timeout=timeout)
                for t in result.tools:
                    schema = {}
                    if hasattr(t, "inputSchema"):
                        sch = t.inputSchema
                        schema = sch.model_dump() if hasattr(sch, "model_dump") else dict(sch)
                    tools.append(MCPTool(
                        server_id=server.id,
                        name=t.name,
                        description=t.description or "",
                        input_schema=schema,
                    ))
        log.info(f"Discovered {len(tools)} tools from '{server.id}'")
    except Exception as e:
        log.warning(f"Could not connect to server '{server.id}' ({server.url}): {e}")

    return tools


async def call_mcp_tool(
    server: MCPServerConfig,
    tool_name: str,
    arguments: dict[str, Any],
    timeout: float = 30.0,
) -> str:
    """
    Invoke a named tool on a remote SSE MCP server and return its text content.
    Raises RuntimeError if the call fails.
    """
    try:
        from mcp.client.sse import sse_client
    except ImportError:
        raise RuntimeError("mcp[sse] not available. Run: pip install 'mcp[cli]'")

    try:
        async with sse_client(server.url) as (read, write):
            async with ClientSession(read, write) as session:
                await asyncio.wait_for(session.initialize(), timeout=timeout)
                result = await asyncio.wait_for(
                    session.call_tool(tool_name, arguments),
                    timeout=timeout,
                )
                parts = []
                for block in result.content:
                    if hasattr(block, "text"):
                        parts.append(block.text)
                return "\n".join(parts)
    except Exception as e:
        raise RuntimeError(
            f"Tool call '{tool_name}' on server '{server.id}' failed: {e}"
        ) from e


class MCPHub:
    """
    Top-level facade used by ERS chains and the CLI.

    Usage:
        hub = MCPHub()
        all_tools = await hub.discover_all()
        result    = await hub.call("jarvis-internal", "search_rag", {"query": "..."})
    """

    def __init__(self, config_path: Path | str | None = None):
        self._servers: list[MCPServerConfig] = load_server_configs(config_path)
        self._server_map: dict[str, MCPServerConfig] = {s.id: s for s in self._servers}

    @property
    def servers(self) -> list[MCPServerConfig]:
        return list(self._servers)

    async def discover_all(self) -> dict[str, list[MCPTool]]:
        """Discover tools from all configured servers (runs concurrently)."""
        coros = {s.id: discover_tools(s) for s in self._servers}
        results: dict[str, list[MCPTool]] = {}
        for sid, coro in coros.items():
            results[sid] = await coro
        return results

    async def call(self, server_id: str, tool_name: str, arguments: dict[str, Any]) -> str:
        """Call a specific tool on a named server by its config id."""
        server = self._server_map.get(server_id)
        if not server:
            raise ValueError(
                f"Unknown MCP server: '{server_id}'. "
                f"Known servers: {list(self._server_map)}"
            )
        return await call_mcp_tool(server, tool_name, arguments)
