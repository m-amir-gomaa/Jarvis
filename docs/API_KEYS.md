# Jarvis API Key & Environment Management

Jarvis utilizes a centralized environment management system to handle API keys and service endpoints. This ensures that sensitive information is kept out of the codebase while remaining easily accessible to the various components.

## 1. The `.env` Configuration
All secrets and environment-specific variables are stored in:
`[JARVIS_ROOT]/config/.env`

If this file does not exist, you can create it by copying the template:
`cp [JARVIS_ROOT]/config/env.example [JARVIS_ROOT]/config/.env`

### Key Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | Primary key for cloud LLM access (Claude, GPT-4, etc.) | None |
| `OLLAMA_BASE_URL` | Local Ollama service endpoint | `http://localhost:11434` |
| `SEARXNG_URL` | Local SearXNG search engine endpoint | `http://localhost:8888` |
| `JARVIS_ROOT` | (Optional) Override path to the Jarvis project | Automatically inferred |

## 2. Managing Keys via CLI
You can inspect the status of your keys and service connections using the built-in command:

```bash
jarvis keys
```

This command will:
- List all recognized environment variables.
- Mask sensitive API key values for privacy.
- Indicate if a key is "Set" or "Not Set".
- Show the current `PYTHONPATH` and `JARVIS_ROOT`.

## 3. Cloud LLM Usage & Budget
Cloud models (accessed via OpenRouter) are only used when:
1. `OPENROUTER_API_KEY` is present in `.env`.
2. The task requires high reasoning (determined by the Model Router).
3. The daily budget defined in `config/budget.toml` has not been exceeded.

If the budget is exhausted, Jarvis will gracefully fallback to local models even if a valid API key is present.

## 4. NixOS Integration
In a NixOS environment, these variables can also be set globally in your `configuration.nix` or via Home Manager, but the `config/.env` file will always take priority if present to allow for quick local overrides.
