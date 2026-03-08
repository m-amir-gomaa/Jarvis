# Jarvis Configuration Guide

Jarvis uses a hierarchical configuration system that allows you to define settings at different levels, from global defaults to project-specific overrides.

## Cascading Resolution Rules

When Jarvis resolves a configuration value, it checks the following locations in order of priority (highest to lowest):

1.  **Local Config**: `<current_directory>/.jarvis/config.toml`
    *   Specific to the project or directory you are currently working in.
2.  **Workspace Config**: `<workspace_root>/.jarvis/workspace.toml`
    *   Applies to all projects within a defined workspace (searched upwards for `.jarvis/workspace.toml`).
3.  **Global Config**: `~/.config/jarvis/config.toml`
    *   Your default settings across all projects.

### Merging Strategy

Jarvis performs a **deep merge** of these configurations. Nested dictionaries are merged recursively, while lists and primitive values at higher priority levels completely overwrite those at lower levels.

## Configuration Files

### `config.toml` / `workspace.toml`

The primary configuration files use the TOML format. Key sections include:

*   `[model_aliases]`: Map friendly names (e.g., "chat", "complete") to specific model strings (e.g., "local/qwen3:14b").
*   `[features]`: Enable or disable specific Jarvis features.
*   `[limits]`: Define token or budget constraints (overrides `budget.toml` if present).

### `.jarvis/mcp.toml`

Project-specific Model Context Protocol (MCP) settings are defined here. This file is specifically for configuring external tools and services that the agent can interact with for a given project.

## Example Configuration

### Global (`~/.config/jarvis/config.toml`)
```toml
[model_aliases]
chat = "local/qwen3:14b"
complete = "local/qwen3:1.7b"

[features]
sse_streaming = true
```

### Local (`project/.jarvis/config.toml`)
```toml
[model_aliases]
# Override chat model for this specific project
chat = "external/openai/gpt-4o"
```

## How it Works (Technical)

The `ConfigResolver` class in `lib/config_resolver.py` handles the resolution logic. It:
1.  Locates the project root (nearest `.git` or `.jarvis` directory).
2.  Identifies the workspace root if applicable.
3.  Loads and merges the TOML files in the defined priority order.
4.  Provides the final unified configuration to the Jarvis server and agents.
