# lib/ers/yaml_schema.py
from typing import Any, Literal
from pydantic import BaseModel, Field

class Conditional(BaseModel):
    """Jinja2 expression evaluation for branching."""
    condition: str
    on_true: str
    on_false: str | None = None

class Step(BaseModel):
    """Schema for an individual execution step within a chain."""
    id: str
    tool: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: list[str] | dict[str, str] = Field(default_factory=list)
    parallel_group: str | None = None
    timeout_seconds: float = 60.0
    allow_partial: bool = False
    on_failure: Literal["retry", "substitute", "correct", "skip", "abort"] = "abort"
    conditionals: list[Conditional] = Field(default_factory=list)

class ExternalAPI(BaseModel):
    """Configuration for an external API dependency."""
    name: str
    base_url: str
    auth_type: str | None = None
    env_vars: list[str] = Field(default_factory=list)

class MetricsConfig(BaseModel):
    """Configuration for metrics collection."""
    enabled: bool = True
    log_level: str = "INFO"

class ToolChainSchema(BaseModel):
    """The enhanced YAML chain schema."""
    id: str
    description: str = ""
    steps: list[Step] = Field(default_factory=list)
    tool_chain: list[str] = Field(default_factory=list)  # Syntactic sugar for linear pipelines
    external_apis: list[ExternalAPI] = Field(default_factory=list)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    conditionals: list[Conditional] = Field(default_factory=list)
