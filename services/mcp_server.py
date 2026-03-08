"""
Jarvis MCP Server

This module implements a Model Context Protocol (MCP) server using FastMCP.
It exposes Jarvis's internal capabilities (like RAG search and web search) 
as tools that can be consumed by any MCP-compatible client.
"""
import sys
import asyncio
from mcp.server.fastmcp import FastMCP
from lib.knowledge_manager import KnowledgeManager
from lib.tools import execute

# Create FastMCP instance
mcp = FastMCP("Jarvis MCP Server")

@mcp.tool()
async def search_rag(query: str) -> str:
    """
    Search Jarvis's internal knowledge base (RAG) using the vector store.

    :param query: The semantic search query string.
    :return: A formatted string containing the most relevant knowledge matches.
    """
    km = KnowledgeManager()
    results = await km.search(query_text=query)
    if not results:
        return "No results found in knowledge base."
    
    output = []
    for r in results:
        title = r.get('source_title', 'Unknown Title')
        layer = r.get('layer', 'Unknown Layer')
        url = r.get('source_url', 'Unknown URL')
        content = r.get('content', '')
        output.append(f"[{title}] ({url}) - Layer {layer}\n{content}")
        
    return "\n\n---\n\n".join(output)

@mcp.tool()
async def search_episodic_memory(query: str, limit: int = 10) -> str:
    """
    Search Jarvis's episodic memory (event log) for recent activities or context.

    :param query: The search query string.
    :param limit: Maximum number of events to return.
    :return: A formatted string of matching events.
    """
    from lib.episodic_memory import search_memory
    events = search_memory(query, limit)
    if not events:
        return "No recent episodic memory found matching the query."
        
    parts = ["## Episodic Memory Results"]
    for e in events:
        parts.append(f"- [{e['ts']}] {e['source']}: {e['event']} ({e['details']})")
    
    return "\n".join(parts)

@mcp.resource("memory://episodic/recent")
def get_recent_episodic_context() -> str:
    """Read-only resource containing the most recent AI/system episodic context."""
    from lib.episodic_memory import get_session_context
    return get_session_context()

@mcp.tool()
async def web_search(query: str) -> str:
    """
    Search the web for information using Jarvis tools.

    :param query: The search query to look up on the web.
    :return: The search results or an error message.
    """
    result = execute("web_search", {"query": query})
    if result.success:
        return result.output
    return f"Search failed: {result.error}"

if __name__ == "__main__":
    transport = "stdio"
    if len(sys.argv) > 1 and sys.argv[1] == "sse":
        transport = "sse"
    
    if transport == "sse":
        # Usually sse transport takes port and host kwargs
        mcp.run(transport="sse", host="127.0.0.1", port=8000)
    else:
        mcp.run(transport="stdio")
