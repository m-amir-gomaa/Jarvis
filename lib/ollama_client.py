import os
import sys
import time
import json
import requests
import tomllib
from typing import List, Dict, Generator, Any, Optional
from filelock import FileLock
from lib.model_router import route
from lib.event_bus import emit

# /home/qwerty/NixOSenv/Jarvis/lib/ollama_client.py

from pathlib import Path

BASE_DIR = Path(os.environ.get("JARVIS_ROOT", Path(__file__).resolve().parent.parent))

CONFIG_PATH = str(BASE_DIR / "config" / "models.toml")
LOCK_PATH = str(BASE_DIR / "logs" / "ollama.lock")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
USER_CONTEXT_PATH = str(BASE_DIR / "config" / "user_context.md")

class OllamaError(Exception):
    pass

class ModelNotFoundError(OllamaError):
    pass

class ConnectionError(OllamaError):
    pass

def _get_model_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)

def is_healthy() -> bool:
    """GET /api/tags — returns True if Ollama is reachable"""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

def list_models() -> List[str]:
    """Returns list of pulled model names"""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags")
        response.raise_for_status()
        models = response.json().get("models", [])
        return [m["name"] for m in models]
    except Exception as e:
        raise OllamaError(f"Failed to list models: {e}")

def _call_api(endpoint: str, payload: Dict[str, Any], stream: bool = False):
    url = f"{OLLAMA_BASE_URL}/api/{endpoint}"
    retries = 3
    backoff = [1, 2, 4]

    for i in range(retries):
        try:
            # Removed global FileLock to allow Ollama internal scheduler to handle concurrency.
            # This prevents 'chat' (14B) from blocking 'classify' (7B) tasks.
            response = requests.post(url, json=payload, stream=stream, timeout=600)
            if response.status_code == 404:
                raise ModelNotFoundError(f"Model '{payload.get('model')}' not found.")
            response.raise_for_status()
            
            if stream:
                emit('ollama', 'chat_started', {'model': payload.get('model'), 'stream': True})
                def gen():
                    for line in response.iter_lines():
                        if line:
                            chunk = json.loads(line)
                            if chunk.get("done"):
                                break
                            yield chunk.get("message", {}).get("content", "") or chunk.get("response", "")
                return gen()
            else:
                res = response.json()
                return res.get("message", {}).get("content", "") or res.get("response", "")
        except (requests.ConnectionError, requests.Timeout) as e:
            if i < retries - 1:
                time.sleep(backoff[i])
                continue
            raise ConnectionError(f"Failed to connect to Ollama at {url}: {e}")
        except requests.RequestException as e:
            raise OllamaError(f"Ollama API error: {e}")

def chat(model_alias: str, messages: List[Dict], system: Optional[str] = None, stream: bool = False, temperature: float = 0.2, thinking: bool = False, num_ctx: int = 4096) -> Any:
    """POST /api/chat. stream=True yields token strings."""
    config = _get_model_config()
    model = config.get("models", {}).get(model_alias, model_alias)
    
    # Prepend system message if provided
    if system:
        messages = [{"role": "system", "content": system}] + messages
        
    # Inject user identity context for chat/reasoning
    if model_alias in ("chat", "fix", "diagnose", "reason") and os.path.exists(USER_CONTEXT_PATH):
        with open(USER_CONTEXT_PATH, "r") as f:
            identity = f.read().strip()
            messages = [{"role": "system", "content": f"User Identity Context:\n{identity}"}] + messages
        
    # Qwen3 Thinking Mode Integration
    if model_alias in ("chat", "fix", "diagnose", "reason"):
        prefix = "/think\n" if thinking else "/no_think\n"
        if messages and messages[-1]['role'] == 'user':
            messages[-1]['content'] = prefix + messages[-1]['content']
        
    # RAM-Aware Keep-Alive Strategy
    keep_alive = "5m"
    if model_alias in ("clean", "summarize", "classify", "score"):
        keep_alive = "0"
    elif model_alias == "complete":
        keep_alive = "10m"

    payload = {
        "model": model,
        "messages": messages,
        "stream": stream,
        "options": {"temperature": temperature, "num_ctx": num_ctx},
        "keep_alive": keep_alive
    }
    
    return _call_api("chat", payload, stream=stream)

def generate(model_alias: str, prompt: str, system: Optional[str] = None, stream: bool = False, suffix: Optional[str] = None, thinking: bool = False) -> Any:
    """POST /api/generate. Single-turn, no history."""
    config = _get_model_config()
    model = config.get("models", {}).get(model_alias, model_alias)
    
    # Qwen3 Thinking Mode
    if model_alias in ("chat", "fix", "diagnose", "reason"):
        prompt = ("/think\n" if thinking else "/no_think\n") + prompt
    
    keep_alive = "5m"
    if model_alias in ("clean", "summarize", "classify", "score"):
        keep_alive = "0"
    elif model_alias == "complete":
        keep_alive = "10m"

    payload = {
        "model": model,
        "prompt": prompt,
        "system": system,
        "stream": stream,
        "options": {"num_ctx": 4096},
        "keep_alive": keep_alive
    }
    if suffix:
        payload["suffix"] = suffix
        
    return _call_api("generate", payload, stream=stream)

def embed(model_alias: str, text: str) -> List[float]:
    """POST /api/embed. Returns embedding vector."""
    config = _get_model_config()
    model = config.get("models", {}).get(model_alias, model_alias)
    
    payload = {"model": model, "input": text}
    url = f"{OLLAMA_BASE_URL}/api/embed"
    
    try:
        response = requests.post(url, json=payload, timeout=600)
        response.raise_for_status()
        emit('ollama', 'embedding_generated', {'model': model})
        return response.json().get("embeddings", [[]])[0]
    except Exception as e:
        raise OllamaError(f"Embedding failed: {e}")

def chat_managed(model_alias: str, messages: List[Dict], system: Optional[str] = None, max_chars: int = 3000, thinking: bool = False, num_ctx: int = 4096) -> str:
    """Summarizes old context before overflow — prevents quality degradation."""
    total_chars = sum(len(m.get("content", "")) for m in messages)
    
    if total_chars > max_chars and len(messages) > 6:
        # Keep system prompt (if any) and last 4 messages, summarize the rest
        to_summarize = messages[:-4]
        keep = messages[-4:]
        
        summary_prompt = "Summarize the preceding conversation concisely while preserving key details and facts."
        summary = chat("summarize", to_summarize, system=summary_prompt, thinking=False)
        
        messages = [{"role": "system", "content": f"Previous conversation summary: {summary}"}] + keep
    
    return chat(model_alias, messages, system=system, thinking=thinking, num_ctx=num_ctx)

if __name__ == "__main__":
    print(f"Health: {is_healthy()}")
    try:
        print(f"Models: {list_models()}")
        # Quick test if models are available
        alias = "embed"
        config = _get_model_config()
        if alias in config.get("models", {}):
            print(f"Testing 'embed' alias...")
            e = embed(alias, "hello world")
            print(f"Embedding length: {len(e)}")
    except Exception as e:
        print(f"Test failed: {e}")
