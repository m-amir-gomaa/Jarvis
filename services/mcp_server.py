import sys
import asyncio
from mcp.server.fastmcp import FastMCP
from lib.knowledge_manager import KnowledgeManager
from lib.tools import execute

# Create FastMCP instance
mcp = FastMCP("Jarvis MCP Server")

@mcp.tool()
async def search_rag(query: str) -> str:
    """Search Jarvis's internal knowledge base (RAG) using the vector store."""
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
async def web_search(query: str) -> str:
    """Search the web for information using Jarvis tools."""
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
