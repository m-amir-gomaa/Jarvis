# /THE_VAULT/jarvis/lib/model_router.py

def route(task: str, context_chars: int = 0, thinking: bool = False) -> str:
    """
    Returns the model alias based on the task and context size.
    'thinking=True' is used for Qwen3 deep reasoning mode.
    """
    rules = {
        'embed': 'embed',
        'complete': 'complete',
        'classify': 'fast',
        'clean': 'chat',
        'summarize': 'chat',
        'score': 'fast',
        'chat': 'chat',
        'fix': 'coder',
        'diagnose': 'coder',
        'reason': 'reason',
    }
    
    # Safety: large context -> swap to fast model
    if context_chars > 6000 and task not in ('fix', 'reason'):
        return 'fast'
        
    # Thinking mode overrides if requested
    if thinking:
        return 'reason'
        
    return rules.get(task, 'chat')
