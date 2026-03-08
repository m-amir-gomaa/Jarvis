# lib/ers/schema.py
from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field


class MCPToolRef(BaseModel):
    """Reference to an MCP tool to call instead of an LLM prompt."""

    server: str             # MCPServerConfig.id from mcp_servers.toml
    tool: str               # Tool name as advertised by the server
    # Arguments template: values may be Jinja2 expressions rendered against exec_ctx
    arguments: dict[str, str] = Field(default_factory=dict)


class ReasoningStep(BaseModel):
    id:               str
    prompt_template:  str = ""       # Empty/omitted when mcp_tool is set
    model_alias:      str = "reason"
    stop_sequences:   list[str] | None = None
    max_tokens:       int = 2048
    on_failure:       Literal["stop", "continue", "retry"] = "stop"
    retry_count:      int = 0
    batch_group:      str | None = None   # Steps with same group run in parallel
    output_key:       str | None = None   # Key for Jinja2 context ({step.id} by default)
    mcp_tool:         MCPToolRef | None = None  # Set to use MCP instead of LLM


class ReasoningChain(BaseModel):
    id:          str
    description: str
    steps:       list[ReasoningStep]
    metadata:    dict[str, Any] = Field(default_factory=dict)

