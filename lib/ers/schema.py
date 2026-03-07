# lib/ers/schema.py
from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

class ReasoningStep(BaseModel):
    id:               str
    prompt_template:  str
    model_alias:      str = "reason"
    stop_sequences:   list[str] | None = None
    max_tokens:       int = 2048
    on_failure:       Literal["stop", "continue", "retry"] = "stop"
    retry_count:      int = 0
    batch_group:      str | None = None  # Steps with same group run in parallel
    output_key:       str | None = None  # Key for Jinja2 context ({step.id} by default)
    
class ReasoningChain(BaseModel):
    id:          str
    description: str
    steps:       list[ReasoningStep]
    metadata:    dict[str, Any] = Field(default_factory=dict)
