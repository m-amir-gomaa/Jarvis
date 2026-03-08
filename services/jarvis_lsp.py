# services/jarvis_lsp.py
from __future__ import annotations
import threading, uvicorn, logging, json, secrets
from pathlib import Path
from pygls.server import LanguageServer
from lsprotocol.types import (
    InitializeParams, INITIALIZE, TEXT_DOCUMENT_COMPLETION,
    CompletionList, CompletionItem, CompletionParams,
    TEXT_DOCUMENT_CODE_ACTION, CodeActionParams, CodeAction
)
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from lib.security.context import SecurityContext
from lib.security.audit import AuditLogger
import asyncio
import queue as _queue
import tomllib
from typing import Any
from lib.models.router import ModelRouter
from lib.security.grants import CapabilityRequest, CapabilityGrantManager
from lib.security.exceptions import CapabilityDenied, TrustLevelError, CapabilityPending

log = logging.getLogger("jarvis.lsp")

LSP_PORT       = 8002
HTTP_PORT      = 8001
import os as _os
JARVIS_ROOT = Path(_os.environ.get("JARVIS_ROOT", Path(__file__).resolve().parent.parent))
REPO_ROOT   = JARVIS_ROOT   # keep REPO_ROOT alias so downstream references don't break

_VAULT_ROOT  = Path(_os.environ.get("VAULT_ROOT", "/THE_VAULT/jarvis"))
SESSION_FILE = _VAULT_ROOT / "context" / "active_session_token"

lsp_server = LanguageServer("jarvis-lsp", "v0.1-phase4")
http_app   = FastAPI()

# ── Security Setup ───────────────────────────────────────────────
audit = AuditLogger()
gm = CapabilityGrantManager(audit_logger=audit)
# Root context for the LSP bridge (acting as parent for clones)
root_ctx = SecurityContext.default("lsp-bridge")

_clone_registry: dict[str, SecurityContext] = {}
_current_conn = threading.local()
_pending_queues: dict[str, _queue.Queue] = {}  # conn_id -> thread-safe Queue

# ── Model Router Setup ────────────────────────────────────────────────────────
def _build_router() -> ModelRouter:
    """Build ModelRouter from config/models.toml."""
    from lib.models.adapters.ollama import OllamaAdapter
    
    config_path = JARVIS_ROOT / "config" / "models.toml"
    config = {}
    if config_path.exists():
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
    
    adapters = {"ollama": OllamaAdapter()}
    
    # Optionally add external adapters if secrets are configured
    try:
        from lib.security.secrets import SecretsManager
        sm = SecretsManager()
        from lib.models.adapters.anthropic import AnthropicAdapter
        from lib.models.adapters.openai import OpenAIAdapter
        from lib.models.adapters.deepseek import DeepSeekAdapter
        from lib.models.adapters.groq import GroqAdapter
        
        adapters["anthropic"] = AnthropicAdapter(sm)
        adapters["openai"] = OpenAIAdapter(sm)
        adapters["deepseek"] = DeepSeekAdapter(sm)
        adapters["groq"] = GroqAdapter(sm)
    except Exception as e:
        log.debug(f"External model adapters not loaded: {e}")
    
    return ModelRouter(config=config, adapters=adapters)

try:
    _router = _build_router()
    log.info("ModelRouter initialized successfully")
except Exception as e:
    log.error(f"ModelRouter initialization failed: {e}")
    _router = None

def _get_clone_ctx(token: str | None, conn_id: str) -> SecurityContext:
    """
    Resolve a session token to a parent SecurityContext, then create a
    bounded child clone. Falls back to root_ctx if token is absent/invalid.
    """
    parent = root_ctx
    authenticated = False
    if token:
        try:
            stored_token = SESSION_FILE.read_text().strip() if SESSION_FILE.exists() else None
            if stored_token and secrets.compare_digest(token, stored_token):
                authenticated = True
            else:
                log.warning(f"LSP token mismatch for conn_id={conn_id}; using anonymous context")
        except Exception as e:
            log.warning(f"Token validation error: {e}")

    ceiling = 2 if authenticated else 1
    return parent.child_context(f"ide-clone-{conn_id}", trust_ceiling=ceiling)

def _get_current_ctx() -> SecurityContext:
    """Get the clone context for the current LSP connection thread."""
    conn_id = getattr(_current_conn, "conn_id", None)
    if conn_id and conn_id in _clone_registry:
        return _clone_registry[conn_id]
    return root_ctx.child_context("ide-clone-anon", trust_ceiling=1)

class SecurityRequest(BaseModel):
    capability: str
    reason:     str
    scope:      str = "task"

class ResolveRequest(BaseModel):
    pending_id: str
    approved:   bool

class IDEFixRequest(BaseModel):
    context: str
    file: str = ""

class IDEExplainRequest(BaseModel):
    text: str

class IDERefactorRequest(BaseModel):
    code: str

class IDETestGenRequest(BaseModel):
    code: str

class IDEDocGenRequest(BaseModel):
    code: str

class IDEChatRequest(BaseModel):
    message: str
    history: list = []

class IDECompleteRequest(BaseModel):
    prefix: str
    file: str = ""
    filetype: str = ""
    max_tokens: int = 64

class IDEReviewRequest(BaseModel):
    code: str

class IDECommitRequest(BaseModel):
    pass  # no body needed; git diff is computed server-side

class IDESearchRequest(BaseModel):
    query: str

class ModelAliasUpdate(BaseModel):
    alias: str
    spec:  str

async def _ide_model_call(
    capability: str,
    reason: str,
    prompt: str,
    model_alias: str = "coder",
    max_tokens: int = 1024,
) -> tuple[str, str | None]:
    """
    Request capability, call model, return (result_text, error_str).
    error_str is None on success.
    """
    if _router is None:
        return "", "ModelRouter not initialized"
    
    ctx = _get_current_ctx()
    
    try:
        gm.request(ctx, CapabilityRequest(
            capability=capability,
            reason=reason,
            scope="task"
        ))
    except CapabilityPending as e:
        conn_id = getattr(_current_conn, "conn_id", None)
        if conn_id and conn_id in _pending_queues:
            _pending_queues[conn_id].put({
                "type": "capability_request",
                "pending_id": e.pending_id,
                "capability": capability,
                "reason": reason,
            })
        return "", f"pending:{e.pending_id}"
    except (CapabilityDenied, TrustLevelError) as e:
        return "", f"denied:{e}"
    
    try:
        result, _usage = await _router.generate(
            model_alias=model_alias,
            prompt=prompt,
            max_tokens=max_tokens,
            ctx=ctx,
        )
        return result.strip(), None
    except Exception as e:
        log.error(f"Model call failed for {capability}: {e}")
        return "", str(e)

@http_app.post("/security/request")
async def request_capability(req: SecurityRequest):
    # In a real multi-session setup, this would resolve a token to a specific parent context.
    # For the bootstrap, we use root_ctx.
    try:
        # Use connection-specific context
        ctx = _get_current_ctx()
        # This will either grant (if auto-allow) or raise CapabilityPending (OOB)
        grant = gm.request(ctx, CapabilityRequest(
            capability=req.capability,
            reason=req.reason,
            scope=req.scope
        ))
        return {"granted": True, "audit_token": grant.audit_token}
    except Exception as e:
        # Check if it's CapabilityPending to return the ID
        from lib.security.exceptions import CapabilityPending
        if isinstance(e, CapabilityPending):
            pending_id = getattr(e, "pending_id", "unknown")
            # Notify the long-poll queue for this connection
            conn_id = getattr(_current_conn, "conn_id", None)
            if conn_id and conn_id in _pending_queues:
                _pending_queues[conn_id].put({
                    "type": "capability_request",
                    "pending_id": pending_id,
                    "capability": req.capability,
                    "reason": req.reason
                })
            return {"granted": False, "pending_id": pending_id, "error": "pending"}
        return {"granted": False, "error": str(e)}

@http_app.get("/security/pending")
async def get_pending_notifications(conn_id: str, timeout: int = 30):
    """
    Long-polling endpoint for OOB security notifications.
    Uses thread-safe queue.Queue + run_in_executor to bridge the LSP thread
    (which calls put()) and the uvicorn event loop (which awaits get()).
    This avoids the asyncio cross-loop RuntimeError from the original asyncio.Queue.
    """
    if conn_id not in _pending_queues:
        _pending_queues[conn_id] = _queue.Queue()

    def _blocking_get():
        try:
            return _pending_queues[conn_id].get(block=True, timeout=timeout)
        except _queue.Empty:
            return None

    loop = asyncio.get_event_loop()
    item = await loop.run_in_executor(None, _blocking_get)
    if item is None:
        return {"status": "timeout"}
    return item

@http_app.post("/security/resolve")
async def resolve_capability(req: ResolveRequest):
    try:
        # Resolve pending for the current context (or root if not found)
        ctx = _get_current_ctx()
        grant = gm.resolve_pending(req.pending_id, ctx, req.approved)
        if grant:
            return {"status": "resolved", "granted": True, "audit_token": grant.audit_token}
        else:
            return {"status": "resolved", "granted": False}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@lsp_server.feature(INITIALIZE)
def on_initialize(params: InitializeParams):
    opts  = params.initialization_options or {}
    token = opts.get("jarvis_session_token") if isinstance(opts, dict) else None

    # Derive unique conn_id: token prefix + random suffix.
    # Two Neovim windows with the same token still get independent clone contexts.
    conn_suffix = secrets.token_hex(4)
    conn_id     = f"{token[:8] if token else 'anon'}-{conn_suffix}"

    ctx = _get_clone_ctx(token, conn_id)
    _clone_registry[conn_id] = ctx

    # Store conn_id in thread-local so subsequent requests from this
    # LSP connection resolve to the right context.
    _current_conn.conn_id = conn_id
    log.info(f"LSP initialized: conn_id={conn_id}, agent_id={ctx.agent_id}, token={'present' if token else 'absent'}")

@lsp_server.feature(TEXT_DOCUMENT_COMPLETION)
def completions(params: CompletionParams):
    """Implement Incomplete Results Pattern (REC-C-01)."""
    log.info(f"Async completion requested for {params.text_document.uri}")
    
    def _compute_and_push():
        # Simulation of expensive 14B model call
        import time
        time.sleep(1.5)
        # In a real imp, we would push a custom notification here
        # or use publishDiagnostics to show ghost text hints.
        log.info("Completion results ready (simulated background task)")

    threading.Thread(target=_compute_and_push, daemon=True).start()
    
    # Return immediately to avoid blocking Neovim UI
    return CompletionList(is_incomplete=True, items=[])

@lsp_server.feature(TEXT_DOCUMENT_CODE_ACTION)
def code_actions(params: CodeActionParams):
    return [
        CodeAction(title="Jarvis: Fix Error", kind="quickfix", command=None),
        CodeAction(title="Jarvis: Explain Concept", kind="refactor", command=None)
    ]

@http_app.get("/health")
async def health():
    return {"status": "ok"}

@http_app.get("/models/list")
async def list_models():
    """List current model aliases and available models."""
    if _router is None:
        raise HTTPException(status_code=500, detail="ModelRouter not initialized")
    
    # Get current mapping
    aliases = _router.get_aliases()
    
    # Get available models from Ollama (best effort)
    available_ollama = []
    try:
        from lib.models.adapters.ollama import OllamaAdapter
        adapter = _router.adapters.get("ollama")
        if isinstance(adapter, OllamaAdapter):
            available_ollama = [m["name"] for m in adapter.list_models()]
    except Exception as e:
        log.warning(f"Failed to list Ollama models: {e}")
    
    return {
        "aliases": aliases,
        "available_ollama": available_ollama,
        "available_providers": list(_router.adapters.keys())
    }

@http_app.post("/models/set_alias")
async def set_model_alias(req: ModelAliasUpdate):
    """Update a model alias at runtime."""
    if _router is None:
        raise HTTPException(status_code=500, detail="ModelRouter not initialized")
    
    try:
        _router.update_alias(req.alias, req.spec)
        return {"status": "ok", "alias": req.alias, "spec": req.spec}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@http_app.get("/auth/conn_id")
async def get_conn_id():
    """Return the conn_id for the most recent LSP connection. Used by Lua setup."""
    conn_id = getattr(_current_conn, "conn_id", None)
    if conn_id:
        return {"conn_id": conn_id}
    return {"conn_id": None}

@http_app.post("/ide/fix")
async def ide_fix(req: IDEFixRequest):
    prompt = (
        f"You are a code repair assistant. Fix the error or issue in the following code.\n"
        f"File: {req.file}\n\n"
        f"Code context:\n{req.context}\n\n"
        f"Return ONLY the fixed code. Do not include explanations or markdown fences.\n"
        f"Preserve the surrounding context and indentation exactly."
    )
    result, error = await _ide_model_call("ide:edit", "Fix code at cursor", prompt, "coder", 2048)
    if error:
        return {"error": error}
    return {"fixed_code": result}


@http_app.post("/ide/explain")
async def ide_explain(req: IDEExplainRequest):
    prompt = (
        f"Explain the following code clearly and concisely. Focus on what it does, "
        f"why it does it, and any non-obvious patterns or gotchas.\n\n"
        f"Code:\n{req.text}"
    )
    result, error = await _ide_model_call("ide:read", "Explain code selection", prompt, "reason", 1024)
    if error:
        return {"error": error}
    return {"explanation": result}


@http_app.post("/ide/refactor")
async def ide_refactor(req: IDERefactorRequest):
    prompt = (
        f"Refactor the following code to improve readability, reduce duplication, "
        f"and follow best practices. Preserve exact behavior.\n\n"
        f"Code:\n{req.code}\n\n"
        f"Return ONLY the refactored code. No explanations, no markdown fences."
    )
    result, error = await _ide_model_call("ide:edit", "Refactor code selection", prompt, "coder", 2048)
    if error:
        return {"error": error}
    return {"refactored": result}


@http_app.post("/ide/test_gen")
async def ide_test_gen(req: IDETestGenRequest):
    prompt = (
        f"Generate comprehensive unit tests for the following code. "
        f"Use pytest. Cover happy paths, edge cases, and error conditions.\n\n"
        f"Code:\n{req.code}\n\n"
        f"Return ONLY the test code. No explanations, no markdown fences."
    )
    result, error = await _ide_model_call("ide:edit", "Generate unit tests", prompt, "coder", 2048)
    if error:
        return {"error": error}
    return {"tests": result}


@http_app.post("/ide/doc_gen")
async def ide_doc_gen(req: IDEDocGenRequest):
    prompt = (
        f"Generate a complete docstring for the following code. "
        f"Include: summary, Args (with types), Returns, Raises (if any), and a usage example.\n\n"
        f"Code:\n{req.code}\n\n"
        f"Return ONLY the docstring (including the triple quotes). No other text."
    )
    result, error = await _ide_model_call("ide:edit", "Generate docstring", prompt, "coder", 512)
    if error:
        return {"error": error}
    return {"docstring": result}


@http_app.post("/ide/chat")
async def ide_chat(req: IDEChatRequest):
    # Build conversation history into prompt
    history_text = ""
    for turn in req.history[-6:]:  # last 3 exchanges (6 turns)
        role = "User" if turn.get("role") == "user" else "Jarvis"
        history_text += f"{role}: {turn.get('content', '')}\n"
    
    prompt = (
        f"You are Jarvis, a personal AI coding assistant. "
        f"Answer concisely and technically.\n\n"
        f"Conversation so far:\n{history_text}"
        f"User: {req.message}\nJarvis:"
    )
    result, error = await _ide_model_call("chat:basic", "IDE chat message", prompt, "chat", 1024)
    if error:
        return {"error": error}
    return {"response": result}


@http_app.post("/ide/complete")
async def ide_complete(req: IDECompleteRequest):
    prompt = (
        f"Complete the following {req.filetype} code. "
        f"Return ONLY the completion text (what comes after the cursor). "
        f"No explanations, no markdown. Maximum {req.max_tokens} tokens.\n\n"
        f"Code prefix:\n{req.prefix}"
    )
    result, error = await _ide_model_call("ide:read", "Inline completion", prompt, "complete", req.max_tokens)
    if error:
        return {"completion": ""}
    return {"completion": result}


@http_app.post("/ide/review")
async def ide_review(req: IDEReviewRequest):
    prompt = (
        f"Perform a thorough code review. Identify: bugs, security issues, "
        f"performance problems, style violations, and improvement opportunities.\n\n"
        f"Code:\n{req.code}\n\n"
        f"Format your response as markdown with sections: "
        f"## Critical Issues, ## Warnings, ## Suggestions, ## Summary"
    )
    result, error = await _ide_model_call("ide:read", "Code review", prompt, "reason", 2048)
    if error:
        return {"error": error}
    return {"review": result}


@http_app.post("/ide/commit")
async def ide_commit(req: IDECommitRequest):
    import subprocess
    try:
        diff_result = subprocess.run(
            ["git", "diff", "--cached"],
            capture_output=True, text=True, timeout=10,
            cwd=str(JARVIS_ROOT)
        )
        diff = diff_result.stdout
        if not diff:
            # Try unstaged diff if nothing staged
            diff_result = subprocess.run(
                ["git", "diff"],
                capture_output=True, text=True, timeout=10,
                cwd=str(JARVIS_ROOT)
            )
            diff = diff_result.stdout
    except Exception as e:
        return {"error": f"git diff failed: {e}"}
    
    if not diff:
        return {"message": "chore: no changes detected"}
    
    prompt = (
        f"Write a conventional commit message for this git diff.\n\n"
        f"Format: <type>(<scope>): <subject>\n"
        f"Rules: subject ≤50 chars, present tense, no period at end.\n"
        f"Types: feat, fix, refactor, docs, test, chore, perf\n\n"
        f"Diff:\n{diff[:3000]}\n\n"  # cap at 3000 chars for token budget
        f"Return ONLY the commit message. No explanation."
    )
    result, error = await _ide_model_call("vcs:read", "Generate commit message", prompt, "coder", 128)
    if error:
        return {"error": error}
    return {"message": result}


@http_app.post("/ide/search")
async def ide_search(req: IDESearchRequest):
    """
    Local semantic search via knowledge manager.
    Falls back to an LLM summary if the knowledge manager is unavailable.
    """
    ctx = _get_current_ctx()
    results = []
    
    try:
        from lib.knowledge_manager import KnowledgeManager
        km = KnowledgeManager()
        raw = km.semantic_search(req.query, top_k=5)
        results = [
            {"title": r.get("category", "result"), "content": r.get("content", ""), "source": r.get("source", "")}
            for r in raw
        ]
    except Exception as e:
        log.warning(f"KnowledgeManager search failed, falling back to LLM: {e}")
        prompt = f"Answer this technical question concisely: {req.query}"
        answer, error = await _ide_model_call("ide:read", "Knowledge search", prompt, "chat", 512)
        if not error:
            results = [{"title": "LLM Response", "content": answer, "source": "local"}]
    
    return {"results": results}

def start_http():
    uvicorn.run(http_app, host="127.0.0.1", port=HTTP_PORT, log_level="warning")

if __name__ == "__main__":
    import secrets # Needed for token_hex
    # Ensure context dir exists
    # Ensure context dir exists in the vault
    (SESSION_FILE.parent).mkdir(parents=True, exist_ok=True)
    
    threading.Thread(target=start_http, daemon=True).start()
    log.info(f"Jarvis LSP starting on TCP {LSP_PORT}, HTTP {HTTP_PORT}")
    lsp_server.start_tcp("127.0.0.1", LSP_PORT)
