# AI Model Management

Jarvis provides flexible, privacy-aware routing and manual management of AI models. You can choose between local models (Ollama) and cloud models (OpenRouter), with support for granular overrides.

## Model Types

1.  **Local Models**: Run on your machine via Ollama. Ideal for private data (`PRIVATE`, `INTERNAL`).
2.  **Cloud Models**: Routed through OpenRouter. Used for `PUBLIC` data when external access is granted.
3.  **Reasoning Models**: Specialized models used for complex planning and code generation.

## CLI Management

### Viewing Models
List available local models, configured aliases, and cloud status:
```bash
jarvis models list
```

### Checking Active Configuration
Show the current effective model mappings, including any session overrides:
```bash
jarvis models active
```

### Selecting Models
You can manually override which model is used for a specific alias:

**Persistent Selection** (saved to `user_prefs.toml`):
```bash
jarvis models select default_local llama3:8b
```

**Session-based Selection** (expires when the session ends):
```bash
jarvis models select reasoning_model qwen:32b --session
```

## Privacy-Aware Routing

Jarvis automatically routes prompts based on data sensitivity:

- **PRIVATE / INTERNAL**: Always routed to the `default_local` model.
- **PUBLIC**: Routed to `default_cloud` if:
    - `model:external` capability is granted.
    - An external provider is enabled in `config/models.toml`.
    - Token budget allows.

## Configuration Files

- `config/models.toml`: System-wide aliases and provider settings.
- `~/.config/jarvis/user_prefs.toml`: User-specific persistent overrides.
- `~/.config/jarvis/context/session_prefs.json`: Temporary session-based overrides.
