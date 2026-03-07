# External Reasoning System (ERS)

ERS allows Jarvis to execute complex multi-step reasoning chains with automated security gating.

## Reasoning Chains
A chain consists of multiple **ReasoningSteps**. Each step:
1. Uses a specified model (local or external).
2. Uses a Jinja2 prompt template to inject outputs from previous steps.
3. Is executed in an isolated child security context.

## Example Chain Definition (JSON)
```json
{
  "id": "research-chain",
  "description": "Research a topic and summarize",
  "steps": [
    {
      "id": "search",
      "model": "external/anthropic/claude-3-haiku",
      "prompt_template": "Search for latest info on {{ topic }}",
      "requires": ["net:search"]
    },
    {
      "id": "summarize",
      "model": "local/qwen",
      "prompt_template": "Summarize this: {{ search_output }}"
    }
  ]
}
```

## Performance
The ERS overhead is minimal (< 1ms per step), ensuring that reasoning delay is almost entirely dependent on LLM inference time.
