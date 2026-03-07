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
from lib.security.grants import CapabilityRequest, CapabilityGrantManager
from lib.security.audit import AuditLogger

log = logging.getLogger("jarvis.lsp")

LSP_PORT       = 8002
HTTP_PORT      = 8001
REPO_ROOT      = Path("/home/qwerty/NixOSenv/Jarvis")
SESSION_FILE   = REPO_ROOT / "context/active_session_token"

lsp_server = LanguageServer("jarvis-lsp", "v0.1-phase4")
http_app   = FastAPI()

# ── Security Setup ───────────────────────────────────────────────
audit = AuditLogger()
gm = CapabilityGrantManager(audit_logger=audit)
# Root context for the LSP bridge (acting as parent for clones)
root_ctx = SecurityContext.default("lsp-bridge")

_clone_registry: dict[str, SecurityContext] = {}

class SecurityRequest(BaseModel):
    capability: str
    reason:     str
    scope:      str = "task"

@http_app.post("/security/request")
async def request_capability(req: SecurityRequest):
    # In a real multi-session setup, this would resolve a token to a specific parent context.
    # For the bootstrap, we use root_ctx.
    try:
        # This will either grant (if auto-allow) or raise CapabilityPending (OOB)
        gm.request(root_ctx, CapabilityRequest(
            capability=req.capability,
            reason=req.reason,
            scope=req.scope
        ))
        return {"granted": True, "audit_token": "todo-token"}
    except Exception as e:
        # CapabilityPending or CapabilityDenied
        return {"granted": False, "error": str(e)}

@lsp_server.feature(INITIALIZE)
def on_initialize(params: InitializeParams):
    token = None
    if params.initialization_options:
        token = params.initialization_options.get("jarvis_session_token")
    
    log.info(f"LSP initialized with token: {token}")
    # Create clone context for this connection
    # Bounded by ELEVATED (2) ceiling
    _clone_registry["default"] = root_ctx.child_context(f"ide-clone-{secrets.token_hex(4)}", trust_ceiling=2)

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

def start_http():
    uvicorn.run(http_app, host="127.0.0.1", port=HTTP_PORT, log_level="warning")

if __name__ == "__main__":
    import secrets # Needed for token_hex
    # Ensure context dir exists
    (REPO_ROOT / "context").mkdir(parents=True, exist_ok=True)
    
    threading.Thread(target=start_http, daemon=True).start()
    log.info(f"Jarvis LSP starting on TCP {LSP_PORT}, HTTP {HTTP_PORT}")
    lsp_server.start_tcp("127.0.0.1", LSP_PORT)
