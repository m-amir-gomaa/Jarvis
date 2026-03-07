import json
import urllib.request
import urllib.error
from typing import Optional, Generator
from lib.budget_controller import BudgetController
from lib.event_bus import emit
from lib.env_manager import load as load_env

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

class CloudClient:
    def __init__(self):
        env = load_env(["OPENROUTER_API_KEY"])
        self.api_key = env["resolved"].get("OPENROUTER_API_KEY")
        self.budget = BudgetController()

    def is_available(self) -> bool:
        """True if OPENROUTER_API_KEY is set AND budget allows cloud calls."""
        if not self.api_key:
            return False
        return not self.budget.is_local_only_mode()

    def chat(self, messages: list[dict], model: str = "anthropic/claude-sonnet-4-5",
             task: str = "chat", system: Optional[str] = None,
             max_tokens: int = 2048, stream: bool = False) -> str | Generator:
        """
        1. Call budget.check_and_reserve(task, estimated_tokens) — ABORT if denied.
        2. Call OpenRouter API.
        3. Call budget.record_usage() with actual token counts from response.
        4. Emit event to event_bus.
        5. Return response text.
        """
        if not self.is_available():
            raise RuntimeError("CloudClient is unavailable (no API key or budget exhausted).")

        # Prepare messages
        payload_messages = []
        if system:
            payload_messages.append({"role": "system", "content": system})
        payload_messages.extend(messages)

        # Estimate tokens
        content_len = sum(len(m.get("content", "")) for m in payload_messages)
        estimated_input = self.budget.estimate_tokens(str(content_len))
        estimated_total = estimated_input + (max_tokens // 2)

        decision = self.budget.check_and_reserve(task, estimated_total)
        if not decision.allowed:
            emit('cloud_client', 'budget_denied', {'task': task, 'reason': decision.reason})
            raise RuntimeError(f"Budget denied: {decision.reason}")

        payload = {
            "model": model,
            "messages": payload_messages,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/m-amir-gomaa/Jarvis",
            "X-Title": "Jarvis",
            "Content-Type": "application/json"
        }

        try:
            if stream:
                # Streaming implementation if requested
                return self._stream_response(payload, headers, model, task)
            else:
                req = urllib.request.Request(
                    f"{OPENROUTER_BASE_URL}/chat/completions",
                    headers=headers,
                    data=json.dumps(payload).encode('utf-8'),
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=300) as response:
                    data = json.loads(response.read().decode())
                    
                content = data["choices"][0]["message"]["content"]
                
                # Record usage
                usage = data.get("usage", {})
                p_tokens = usage.get("prompt_tokens", estimated_input)
                o_tokens = usage.get("completion_tokens", self.budget.estimate_tokens(content))
                
                self.budget.record_usage(model, task, p_tokens, o_tokens)
                emit('cloud_client', 'chat_completed', {
                    'model': model, 'task': task, 'prompt_tokens': p_tokens, 'output_tokens': o_tokens
                })
                
                return content
                
        except Exception as e:
            emit('cloud_client', 'error', {'error': str(e)})
            raise RuntimeError(f"CloudClient error: {e}")

    def _stream_response(self, payload: dict, headers: dict, model: str, task: str) -> Generator:
        req = urllib.request.Request(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            data=json.dumps(payload).encode('utf-8'),
            method="POST"
        )
        
        full_content = []
        with urllib.request.urlopen(req, timeout=300) as response:
            for line in response:
                if line:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        data_str = line[6:]
                        if data_str == '[DONE]':
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk['choices'][0].get('delta', {})
                            if 'content' in delta:
                                text = delta['content']
                                full_content.append(text)
                                yield text
                        except json.JSONDecodeError:
                            pass
        
        content = "".join(full_content)
        # We don't have accurate token counts for streams from OpenRouter dynamically, so we estimate
        est_input = self.budget.estimate_tokens(str(payload))
        est_output = self.budget.estimate_tokens(content)
        self.budget.record_usage(model, task, est_input, est_output)
        emit('cloud_client', 'stream_completed', {
            'model': model, 'task': task, 'prompt_tokens': est_input, 'output_tokens': est_output
        })

