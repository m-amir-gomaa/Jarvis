import os
from typing import Optional, Generator

from lib.model_router import route, Privacy, RouteDecision
from lib.cloud_client import CloudClient
from lib.ollama_client import _call_api as ollama_call_api, chat as ollama_chat
from lib.budget_controller import BudgetController
from lib.event_bus import emit
from lib.working_memory import WorkingMemory

_cloud_client = None

def get_cloud_client() -> CloudClient:
    global _cloud_client
    if _cloud_client is None:
        _cloud_client = CloudClient()
    return _cloud_client

def ask(prompt: Optional[str] = None,
        task: str = 'chat',
        privacy: Privacy = Privacy.INTERNAL,
        context_tokens: int = 0,
        thinking: bool = False,
        system: Optional[str] = None,
        messages: Optional[list] = None,
        stream: bool = False,
        path: Optional[str] = None) -> str | Generator:
    """
    Unified entry point for LLM interactions.
    """
    wm = WorkingMemory()
    
    # Build messages if only prompt provided
    original_prompt = prompt
    if messages is None:
        messages = [{"role": "user", "content": prompt or ""}]
        
    # Prepend working memory context before the user's latest message, but after the system prompt (which isn't in messages yet)
    context_msgs = wm.get_context_messages()
    
    # Check if context messages already exist in the passed list (to avoid duplication on retries)
    if context_msgs and messages:
        if not messages or messages[0].get("content") != context_msgs[0].get("content"):
            # Put memory history before the current interaction
            messages = context_msgs + messages
        
    budget = BudgetController()
    cloud = get_cloud_client()
    budget_ok = cloud.is_available()  # Cloud allowed if key exists and budget is OK
        
    # Get routing decision
    decision = route(
        task=task,
        privacy=privacy,
        context_tokens=context_tokens,
        thinking=thinking,
        budget_ok=budget_ok,
        path=path or os.getcwd() # Default to current dir for privacy checks
    )
    
    emit('llm', 'route_decision', {
        'task': task,
        'backend': decision.backend,
        'model': decision.model_alias,
        'reasoning': decision.reasoning,
        'privacy': privacy.value
    })

    if decision.backend == 'cloud':
        # Delegate to CloudClient
        if thinking:
            # Combine system with thinking instructions if necessary, though CloudClient just passes it
            pass
        response = cloud.chat(
            messages=messages,
            model=decision.model_alias,
            task=task,
            system=system,
            stream=stream
        )
    else:
        # Delegate to OllamaClient
        response = ollama_chat(
            model_alias=decision.model_alias,
            messages=messages,
            system=system,
            thinking=thinking,
            stream=stream
        )
        
    # Save the interaction to memory
    if original_prompt:
        wm.save_turn("user", original_prompt)
    elif messages and messages[-1].get("role") == "user":
        # Save the last user message
        wm.save_turn("user", messages[-1].get("content", ""))
        
    if not stream and isinstance(response, str):
        wm.save_turn("assistant", response)
        
    return response
