# 🔌 Model Context Protocol (MCP) Integration

Jarvis V3 implements the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/), allowing it to seamlessly interoperate with external tools and expose its own capabilities to other AI agents.

---

## 1. Overview

MCP enables a standardized way for AI models to:
1.  **Consume Tools**: Connect to external servers (like Google Drive, Slack, or local filesystems) and call their tools.
2.  **Expose Tools**: Offer internal capabilities (like Jarvis's RAG search) to other clients.

Jarvis acts as both an **MCP Host** and an **MCP Server**.

---

## 2. Jarvis as an MCP Host (Consuming Tools)

Jarvis can connect to any MCP server that communicates over `stdio`. This allows Jarvis to use tools it wasn't originally programmed with.

### Configuration (`mcp.toml`)
Configure external servers in `.jarvis/mcp.toml` within your project root:

```toml
[[servers]]
name = "filesystem"
command = "npx"
args = ["@modelcontextprotocol/server-filesystem", "/path/to/allowed/dir"]

[[servers]]
name = "postgres"
command = "npx"
args = ["@modelcontextprotocol/server-postgres", "postgresql://localhost/mydb"]
```

### Usage in Neovim
1.  Open the MCP Tool Picker: `<leader>jt` (or `:JarvisMCP`).
2.  Select a tool from the discovered list.
3.  Jarvis will execute the tool and provide the results.

---

## 3. MCP Tool Hub & Discovery

Jarvis V3.5 introduces a centralized **Tool Hub** that manages multiple MCP servers and enables dynamic tool discovery. This allows Jarvis to orchestrate tools across different protocols (SSE and Stdio) within the same reasoning session.

### Centralized Configuration (`config/mcp_servers.toml`)
External servers are managed in `config/mcp_servers.toml`:

```toml
[[servers]]
id      = "jarvis-internal"
name    = "Jarvis Internal MCP Server"
type    = "sse"
url     = "http://127.0.0.1:8000/sse"
enabled = true

[[servers]]
id      = "file-manager"
name    = "Local File Manager"
type    = "stdio"
command = "python3 /path/to/server.py"
enabled = false
```

### Discovery Mechanism
The `MCPHub` (`lib/mcp_client.py`) automatically:
1.  Loads all `enabled` servers from the TOML config.
2.  Performs concurrent discovery of tools across all servers.
3.  Exposes a unified `call(server_id, tool_name, arguments)` interface used by ERS chains.

---

## 4. Jarvis as an MCP Server (Exposed Capability)

Jarvis runs a dedicated MCP server (`services/mcp_server.py`) that exposes its core intelligence to other MCP-compatible clients (like Claude Desktop or other agents).

### Exposed Tools
-   **`search_rag`**: Semantic search across Jarvis's vector store.
-   **`search_episodic_memory`**: Search the event log for recent activities.
-   **`web_search`**: Live web search results.

### Exposed Resources
Jarvis exposes internal state as read-only resources:
-   **`memory://episodic/recent`**: Provides the current session context and recent events as a continuous text stream.

### Connecting to Jarvis MCP
Point your MCP client to the Jarvis MCP entrypoint:

**Via Stdio (Recommended):**
```bash
python3 services/mcp_server.py
```

**Via SSE (Experimental):**
```bash
python3 services/mcp_server.py sse
```

---

## 4. Technical Architecture

-   **`lib/mcp_client.py`**: Implementation of `MCPHub`, `MCPClient`, and discovery logic.
-   **`services/mcp_server.py`**: Built on `FastMCP`, exposing tools and memory resources.
-   **`config/mcp_servers.toml`**: The registry of trusted tool providers.
-   **`lua/jarvis/mcp.lua`**: Telescope integration for Neovim.

---

## 5. Security & Trust

All MCP tool calls are governed by Jarvis's **Capability-Based Access Control (CBAC)**.
-   When a tool is called, Jarvis checks the `SecurityContext`.
-   External tool executions are logged in the **Jarvis Dashboard** audit trail.
-   Sensitive tools (like filesystem write) require explicit user approval if not auto-granted.

---

*For more information on the protocol, visit [modelcontextprotocol.io](https://modelcontextprotocol.io/).*
