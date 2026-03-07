# JARVIS BOOTSTRAP — MODEL HUB & IDE BRIDGE
**Read BOOTSTRAP_CORE.md first.**

---

## PART A: MODEL HUB (lib/models/)

### Files

```
lib/models/
  __init__.py
  router.py           # ModelRouter — alias resolution + adapter dispatch
  adapters/
    base.py           # ModelAdapter ABC
    ollama.py         # Local Ollama (always available)
    anthropic.py      # Claude
    openai.py         # GPT (model arg fixed in V3)
    gemini.py         # Google Gemini
    deepseek.py       # DeepSeek
    groq.py           # Groq
    mistral.py        # Mistral
```

### ModelAdapter ABC (base.py)

```python
class ModelAdapter(ABC):
    @abstractmethod
    async def generate(self, model: str, prompt: str,
                       stop: list[str] | None = None,
                       max_tokens: int = 1024, **kwargs) -> tuple[str, dict[str, int]]:
        """Returns (text, usage_dict)"""

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if this provider is reachable."""
```

### ModelRouter API

```python
from lib.models.router import ModelRouter

router = ModelRouter(config=models_config, adapters={
    "ollama":    OllamaAdapter(),
    "anthropic": AnthropicAdapter(secrets_manager),
    "openai":    OpenAIAdapter(secrets_manager),
    "gemini":    GeminiAdapter(secrets_manager),
})

# Async (use from async context / ERS)
text, usage = await router.generate("coder", "Fix this bug: ...", ctx=security_ctx)

# Sync (use from sync context / CLI)
text, usage = router.call("reason", "Explain this error: ...")
```

### Model Alias Resolution

Defined in `config/models.toml` under `[aliases]`:

| Alias | Default Target | Notes |
|-------|---------------|-------|
| `reason` | `local/qwen3:14b-q4_K_M` | Heavy — best quality |
| `chat` | `local/qwen3:8b` | Medium — general chat |
| `fast` | `local/qwen3:1.7b` | Tiny — low latency |
| `coder` | `local/qwen2.5-coder:7b-instruct` | Code tasks |
| `complete` | `local/qwen3:1.7b` | Ghost-text completions |
| `embed` | `local/nomic-embed-text:latest` | Embeddings |

Spec string format: `"local/<ollama-model>"` or `"external/<provider>/<model>"`

Examples:
```toml
[aliases]
reason = "local/qwen3:14b-q4_K_M"
fast_external = "external/anthropic/claude-3-5-haiku-20241022"
```

### Routing Logic (ModelRouter.generate)

```
1. resolve alias → model spec
2. parse spec → (provider, model_name)
3. if ctx: enforce model:local (ollama) or model:external (others)
4. check adapter.is_available()
5. if unavailable + fallback_on_fail → use ollama
6. call adapter.generate(model_name, prompt, ...)
```

### Synchronous Wrapper (call)

```python
def call(self, model_alias, prompt, **kwargs):
    loop = asyncio.get_event_loop()  # or new_event_loop()
    return loop.run_until_complete(self.generate(model_alias, prompt, **kwargs))
```

`nest_asyncio` imported and applied at module level — allows `run_until_complete` inside a running loop (needed for FastAPI routes calling `router.call()`).

### API Key Setup

```python
from lib.security.secrets import SecretsManager
sm = SecretsManager()
sm.set("ANTHROPIC_API_KEY", "sk-ant-...")
sm.set("OPENAI_API_KEY", "sk-...")
sm.set("GOOGLE_API_KEY", "...")
```

Keyring location: `/THE_VAULT/jarvis/secrets/.keyring`

### Config (config/models.toml structure)

```toml
[aliases]
reason   = "local/qwen3:14b-q4_K_M"
coder    = "local/qwen2.5-coder:7b-instruct"
chat     = "local/qwen3:8b"

[routing]
default_local    = "qwen3:14b-q4_K_M"
default_external = "anthropic/claude-3-5-haiku-20241022"
fallback_on_fail = true

[providers.ollama]
enabled = true
base_url = "http://localhost:11434"

[providers.anthropic]
enabled = false   # set true when key is set

[providers.openai]
enabled = false
```

---

## PART B: IDE BRIDGE (services/jarvis_lsp.py + lua/jarvis/ide/)

### jarvis_lsp.py Architecture

```
FastAPI app (uvicorn, port 8001):
  GET  /health              → {"status":"ok"}
  POST /security/request    → CapabilityGrantManager.request()
  GET  /security/pending    → Long-poll (timeout param, max 30s)
  POST /security/resolve    → resolve_pending()
  GET  /auth/conn_id        → thread_local.conn_id (FIXME: AttributeError before first LSP conn)
  POST /ide/fix             → ERS clone_code_action chain
  POST /ide/explain         → ModelRouter.call("reason", ...)
  POST /ide/refactor        → ERS clone_code_action chain
  POST /ide/test_gen        → ModelRouter.call("coder", ...)
  POST /ide/doc_gen         → ModelRouter.call("coder", ...)
  POST /ide/commit          → ModelRouter.call("fast", ...)
  POST /ide/review          → ERS clone_code_review chain
  POST /ide/search          → KnowledgeManager.search()
  POST /ide/chat            → ModelRouter.call("chat", ...)
  POST /ide/model           → List available models

pygls LSP server (TCP, port 8002):
  Receives LSP messages from Neovim
  Registers session → sets thread_local.conn_id
  Routes LSP requests to security-gated handlers
```

### Session Token & Clone Context

```python
# On every jarvis.py startup:
SESSION_FILE = VAULT_ROOT / "context" / "active_session_token"
def _ensure_session_token():
    if not SESSION_FILE.exists():
        token = secrets.token_hex(16)
        SESSION_FILE.write_text(token)
        SESSION_FILE.chmod(0o600)

# When LSP connection arrives:
def _get_clone_ctx(conn_id, token):
    authenticated = False
    if token:
        stored = SESSION_FILE.read_text().strip()
        if secrets.compare_digest(token, stored):
            authenticated = True
    ceiling = 2 if authenticated else 1
    return root_ctx.child_context(f"ide-clone-{conn_id}", trust_ceiling=ceiling)
```

### IDE Route Pattern

All IDE routes follow this pattern:

```python
@app.post("/ide/fix")
async def ide_fix(req: IDERequest, authorization: str = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else None
    ctx = _get_clone_ctx(_get_current_ctx_id(), token)
    try:
        ctx.require("ide:edit")
    except CapabilityDenied:
        raise HTTPException(403, "ide:edit not granted")
    # ... call ERS or ModelRouter
```

### Lua IDE Layer

```
lua/jarvis/ide/
  init.lua        → M.setup(opts); registers keybinds; calls lsp.setup + security.setup
  security.lua    → M.request_capability(cap, reason, callback); M._poll_pending()
  actions.lua     → 10 actions (ALL now gate on security.request_capability)
  lsp.lua         → lspconfig.jarvis setup; on_attach + conn_id deferred fetch
  inline.lua      → textDocument/didChange → ghost-text (debounce NOT wired)
  chat.lua        → :JarvisIDEChat buffer management
```

### Neovim Setup (from jarvis.lua plugin config)

```lua
require("jarvis.ide").setup({
  session_token = vim.fn.readfile(os.getenv("VAULT_ROOT") .. "/context/active_session_token")[1],
  conn_id = nil,    -- filled by lsp.lua on_attach deferred fetch
})
```

### Capability Guards in Lua (actions.lua pattern)

```lua
-- ALL actions follow this pattern:
function M.fix()
  security.request_capability("ide:edit", "Fix code at cursor", function(granted)
    if not granted then
      notify("ide:edit capability denied", vim.log.levels.WARN)
      return
    end
    -- ... do the action
  end)
end

-- Capability assignment:
-- explain, review, search, commit, chat, model → "ide:read"  (floor 1, auto-granted)
-- fix, refactor, test_gen, doc_gen             → "ide:edit"  (floor 2, requires authenticated LSP)
```

### conn_id Flow (lsp.lua)

```lua
-- 500ms after LSP attach:
vim.defer_fn(function()
  local result = vim.fn.system("curl -s http://localhost:8001/auth/conn_id")
  -- NOTE: vim.fn.system() is BLOCKING — should be jobstart() (low priority TODO)
  local ok, data = pcall(vim.fn.json_decode, result)
  if ok and data and data.conn_id then
    require("jarvis.ide.security").set_conn_id(data.conn_id)
  end
end, 500)
```

### OOB Long-Poll (security.lua)

```lua
-- Maximum 6 attempts × 10s each = 60s total
-- _active_poll guard ensures only ONE curl is running at a time
-- On timeout: user sees notification "Run: jarvis approve <id>"
-- URL: /security/pending?timeout=10&conn_id=<conn_id>
```

### Known Issues

- `/auth/conn_id` raises `AttributeError` if called before first LSP connection.
  Fix: `getattr(_thread_local, "conn_id", None)` guard needed.
- `inline.lua` debounce_ms not applied — fires on every keystroke. Low priority.
- `lsp.lua` conn_id fetch uses blocking `vim.fn.system()` — should be `jobstart`.
