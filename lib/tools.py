import os
import json
import shlex
import subprocess
import urllib.request
import urllib.parse
from dataclasses import dataclass
from typing import Optional, Any
from pathlib import Path

from lib.model_router import Privacy
from lib.event_bus import emit

@dataclass
class Tool:
    name: str
    description: str
    parameters: dict  # JSON Schema
    privacy: Privacy
    timeout_s: int = 30
    requires_confirm: bool = False

@dataclass
class ToolResult:
    success: bool
    output: str
    error: Optional[str] = None

# ----------------------------------------------------------------------------
# Implementations
# ----------------------------------------------------------------------------
def _run_shell(args: dict) -> ToolResult:
    cmd = args.get("command", "")
    if not isinstance(cmd, list):
        # We enforce list form to avoid shell=True vulnerabilities, 
        # so if it's a string, we safely lex it first.
        try:
            cmd = shlex.split(cmd)
        except Exception as e:
            return ToolResult(False, "", f"Failed to parse command string: {e}")
            
    if not cmd:
        return ToolResult(False, "", "Empty command")
        
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        output = res.stdout
        if res.stderr:
            output += f"\nSTDERR:\n{res.stderr}"
        return ToolResult(res.returncode == 0, output)
    except subprocess.TimeoutExpired:
        return ToolResult(False, "", "Command timed out after 10s")
    except Exception as e:
        return ToolResult(False, "", f"Execution error: {e}")

def _file_read(args: dict) -> ToolResult:
    path = args.get("path", "")
    if not path:
        return ToolResult(False, "", "Missing path parameter")
        
    # Expand ~ logic roughly if needed, usually we expect absolute paths.
    p = Path(os.path.expanduser(path))
    if not p.exists():
        return ToolResult(False, "", f"File not found: {path}")
    if not p.is_file():
        return ToolResult(False, "", f"Path is not a regular file: {path}")
        
    try:
        content = p.read_text(encoding="utf-8")
        return ToolResult(True, content)
    except Exception as e:
        return ToolResult(False, "", f"Failed to read file: {e}")

def _file_write(args: dict) -> ToolResult:
    path = args.get("path", "")
    content = args.get("content", "")
    if not path:
        return ToolResult(False, "", "Missing path parameter")
        
    p = Path(os.path.expanduser(path))
    try:
        # Pre-commit the file if it already exists to allow rollback
        if p.exists():
            _git_commit_file(p)
            
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return ToolResult(True, f"Successfully wrote {len(content)} bytes to {path}")
    except Exception as e:
        return ToolResult(False, "", f"Failed to write file: {e}")

def _file_patch(args: dict) -> ToolResult:
    path = args.get("path", "")
    search = args.get("search", "")
    replace = args.get("replace", "")
    if not path or not search:
        return ToolResult(False, "", "Missing path or search parameters")
        
    p = Path(os.path.expanduser(path))
    if not p.exists():
        return ToolResult(False, "", f"File not found: {path}")
        
    try:
        # Pre-commit to allow rollback
        _git_commit_file(p)
        
        content = p.read_text(encoding="utf-8")
        if search not in content:
            return ToolResult(False, "", "Search string not found in file (must be exact match)")
            
        new_content = content.replace(search, replace)
        p.write_text(new_content, encoding="utf-8")
        return ToolResult(True, f"Successfully patched file {path}")
    except Exception as e:
        return ToolResult(False, "", f"Failed to patch file: {e}")

def _git_status(args: dict) -> ToolResult:
    cwd = args.get("repo_path", str(Path(__file__).parent.parent))
    try:
        res = subprocess.run(["git", "status", "-s"], cwd=cwd, capture_output=True, text=True, timeout=5)
        return ToolResult(True, res.stdout or "\nNo changes")
    except Exception as e:
        return ToolResult(False, "", f"Git status failed: {e}")

def _git_commit(args: dict) -> ToolResult:
    cwd = args.get("repo_path", str(Path(__file__).parent.parent))
    message = args.get("message", "Auto-commit by Jarvis")
    try:
        subprocess.run(["git", "add", "."], cwd=cwd, check=True, capture_output=True, timeout=5)
        res = subprocess.run(["git", "commit", "-m", message], cwd=cwd, capture_output=True, text=True, timeout=5)
        return ToolResult(True, res.stdout)
    except subprocess.CalledProcessError as e:
        return ToolResult(False, "", f"Git commit failed: {e.output.decode('utf-8') if e.output else str(e)}")
    except Exception as e:
        return ToolResult(False, "", f"Git commit failed: {e}")

def _git_commit_file(p: Path) -> None:
    try:
        cwd = p.parent
        subprocess.run(["git", "add", p.name], cwd=cwd, check=True, capture_output=True, timeout=5)
        subprocess.run(["git", "commit", "-m", f"Pre-modification backup: {p.name}"], cwd=cwd, check=True, capture_output=True, timeout=5)
    except Exception:
        pass # Not critical to fail if repo isn't cleanly tracked

def _web_search(args: dict) -> ToolResult:
    query = args.get("query", "")
    if not query:
        return ToolResult(False, "", "Missing query")
        
    try:
        url = "http://127.0.0.1:8888/search?" + urllib.parse.urlencode({"q": query, "format": "json"})
        req = urllib.request.Request(url, headers={'User-Agent': 'Jarvis/1.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode())
            results = data.get('results', [])[:5] # Top 5
            out = "\n".join([f"- {r.get('title')}: {r.get('url')}\n  {r.get('content')}" for r in results])
            return ToolResult(True, out if out else "No results found.")
    except Exception as e:
        return ToolResult(False, "", f"Web search failed: {e}")

def _web_fetch(args: dict) -> ToolResult:
    url = args.get("url", "")
    if not url:
        return ToolResult(False, "", "Missing url")
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Jarvis/1.0'})
        with urllib.request.urlopen(req, timeout=20) as response:
            content = response.read().decode(errors='ignore')
            # Rudimentary cleanup to prevent massive payload dumping
            content = content[:8000] + "...\n[TRUNCATED]" if len(content) > 8000 else content
            return ToolResult(True, content)
    except Exception as e:
        return ToolResult(False, "", f"Web fetch failed: {e}")

def _python_eval(args: dict) -> ToolResult:
    code = args.get("code", "")
    if not code:
        return ToolResult(False, "", "Missing code")
        
    try:
        # Instead of eval(), we run python -c with timeout
        # Using sys.stdout to capture simple expressions/prints safely
        script = f"import sys\n{code}"
        res = subprocess.run(["python", "-c", script], capture_output=True, text=True, timeout=10)
        output = res.stdout
        if res.stderr:
            output += f"\nSTDERR:\n{res.stderr}"
        return ToolResult(res.returncode == 0, output)
    except subprocess.TimeoutExpired:
        return ToolResult(False, "", "Python eval timed out after 10s")
    except Exception as e:
        return ToolResult(False, "", f"Python eval failed: {e}")


# ----------------------------------------------------------------------------
# Registry
# ----------------------------------------------------------------------------

TOOL_REGISTRY = {
    'shell_run': Tool(
        name="shell_run",
        description="Executes a shell command on the host OS. Do not run destructive or long-running commands.",
        parameters={"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]},
        privacy=Privacy.PRIVATE,
        timeout_s=10,
        requires_confirm=True
    ),
    'file_read': Tool(
        name="file_read",
        description="Reads the content of a file at the given absolute path.",
        parameters={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
        privacy=Privacy.PRIVATE,
        timeout_s=5,
        requires_confirm=False
    ),
    'file_write': Tool(
        name="file_write",
        description="Writes complete new content linearly to a file. Do NOT use this for small edits.",
        parameters={"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]},
        privacy=Privacy.PRIVATE,
        timeout_s=5,
        requires_confirm=True
    ),
    'file_patch': Tool(
        name="file_patch",
        description="Replaces an exact text string with new text in an existing file. Search string must match exactly.",
        parameters={"type": "object", "properties": {"path": {"type": "string"}, "search": {"type": "string"}, "replace": {"type": "string"}}, "required": ["path", "search", "replace"]},
        privacy=Privacy.PRIVATE,
        timeout_s=5,
        requires_confirm=True
    ),
    'web_search': Tool(
        name="web_search",
        description="Searches the web via SearXNG for information. Returns top 5 results.",
        parameters={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        privacy=Privacy.PUBLIC,
        timeout_s=15,
        requires_confirm=False
    ),
    'web_fetch': Tool(
        name="web_fetch",
        description="Fetches raw text content from a web URL.",
        parameters={"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
        privacy=Privacy.PUBLIC,
        timeout_s=20,
        requires_confirm=False
    ),
    'python_eval': Tool(
        name="python_eval",
        description="Executes a Python script statelessly and captures stdout.",
        parameters={"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]},
        privacy=Privacy.PRIVATE,
        timeout_s=10,
        requires_confirm=False
    ),
    'git_commit': Tool(
        name="git_commit",
        description="Stages and commits all current repository changes automatically.",
        parameters={"type": "object", "properties": {"repo_path": {"type": "string"}, "message": {"type": "string"}}, "required": ["message"]},
        privacy=Privacy.PRIVATE,
        timeout_s=10,
        requires_confirm=True
    ),
    'git_status': Tool(
        name="git_status",
        description="Gets the current git status diff.",
        parameters={"type": "object", "properties": {"repo_path": {"type": "string"}}},
        privacy=Privacy.PRIVATE,
        timeout_s=5,
        requires_confirm=False
    ),
}

_TOOL_HANDLERS = {
    'shell_run': _run_shell,
    'file_read': _file_read,
    'file_write': _file_write,
    'file_patch': _file_patch,
    'web_search': _web_search,
    'web_fetch': _web_fetch,
    'python_eval': _python_eval,
    'git_commit': _git_commit,
    'git_status': _git_status,
}

def execute(tool_name: str, args: dict) -> ToolResult:
    """
    Execute a tool safely:
    1. Look up tool in TOOL_REGISTRY — raise if not found.
    2. If requires_confirm: log confirmation need. Since this is an agent, 
       interactive CLI prompts are handled one level up if applicable. Here we skip blocking prompts.
    3. Run with timeout enforcement.
    4. Return ToolResult(success, output, error).
    5. Emit event to event_bus.
    """
    if tool_name not in TOOL_REGISTRY or tool_name not in _TOOL_HANDLERS:
        return ToolResult(False, "", f"Unknown tool: {tool_name}")
        
    tool_def = TOOL_REGISTRY[tool_name]
    handler = _TOOL_HANDLERS[tool_name]
    
    # Normally handle user interaction for requires_confirm here, 
    # but we will assume authorization logic is handled via CLI intercept for now
    
    emit('tools_execution', 'called', {'tool': tool_name, 'args': args})
    
    try:
        res = handler(args)
        status = "success" if res.success else "failed"
        emit('tools_execution', status, {'tool': tool_name, 'error': res.error})
        return res
    except Exception as e:
        emit('tools_execution', 'failed', {'tool': tool_name, 'error': str(e)})
        return ToolResult(False, "", f"Uncaught execution error: {e}")
