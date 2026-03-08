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

## 3. Jarvis as an MCP Server (Exposing Tools)

Jarvis runs a dedicated MCP server (`services/mcp_server.py`) that exposes its core intelligence to other MCP-compatible clients (like Claude Desktop or other agents).

### Exposed Tools
-   **`search_rag`**: Performs a semantic search across Jarvis's internal knowledge base.
-   **`web_search`**: Uses Jarvis's search tools to find information on the live web.

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

-   **`lib/mcp_client.py`**: A robust Python implementation of an MCP client using `AsyncExitStack` for reliable resource management.
-   **`services/mcp_server.py`**: Built on `FastMCP` for high-performance tool exposure.
-   **`lua/jarvis/mcp.lua`**: Telescope integration for a native Neovim experience.

---

## 5. Security & Trust

All MCP tool calls are governed by Jarvis's **Capability-Based Access Control (CBAC)**.
-   When a tool is called, Jarvis checks the `SecurityContext`.
-   External tool executions are logged in the **Jarvis Dashboard** audit trail.
-   Sensitive tools (like filesystem write) require explicit user approval if not auto-granted.

---

*For more information on the protocol, visit [modelcontextprotocol.io](https://modelcontextprotocol.io/).*
