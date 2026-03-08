# Internal: Hybrid Model Router

The `ModelRouter` is the intelligent traffic controller for Jarvis, deciding whether to route a request to a local LLM (Ollama) or a high-capacity cloud provider (Gemini/OpenAI).

## 🏗️ Logic

### Alias System (`lib/model_router.py`)
Jarvis uses logical aliases instead of hardcoded model names:
*   `chat`: High-reasoning (e.g., Qwen 14B or Gemini 1.5 Pro).
*   `complete`: Fast, low-latency FIM (e.g., Qwen 1.7B).
*   `fix`: Large context agentic loop.

### Routing Strategy
1.  **Preference Check**: Respects `config/prefs.toml` settings.
2.  **Health Check**: Verifies if local `ollama` is active before routing locally.
3.  **Budget Guard**: Cloud requests are gated by `lib/budget_controller.py` to prevent cost overruns.
4.  **Semantic Routing**: Analyze prompt complexity to choose between local (fast/private) and cloud (smart/heavy).

### Prefetching (`/prefetch` endpoint)
The router supports "warm-starting" models. When Neovim detects a user entering a Python file or Insert mode, it signals the router to load the relevant models into VRAM/RAM during idle time.

## ⚙️ Configuration

Aliases are mapped in `~/.jarvis/config/models.json`. 

Example:
```json
{
  "aliases": {
    "chat": "local/qwen3:14b-q4_K_M",
    "complete": "local/qwen3:1.7b"
  }
}
```

## 🛠️ Commands

Update an alias via CLI:
```bash
jarvis models set-alias chat external/gemini/gemini-1.5-pro
```
Or via Neovim:
```vim
:JarvisModel
```
