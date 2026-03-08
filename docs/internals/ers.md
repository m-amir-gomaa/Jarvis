# Internal: External Reasoning System (ERS)

The ERS (External Reasoning System) is a post-processing and validation layer in Jarvis v3.5 that ensures LLM outputs meet strict structural and logical requirements.

## 🏗️ Architecture

The ERS operates as a pipeline centered around `lib/ers/chain.py`. It bridges the gap between raw LLM text generation and structured tool execution.

### Core Components

1.  **YAML Schema Validation (`lib/ers/yaml_schema.py`)**:
    *   Uses **Pydantic** to enforce schemas on LLM outputs.
    *   Ensures that when an agent proposes a "plan" or "tool call", it follows the exact format required by the system.
    
2.  **Parallel Executor (`lib/ers/parallel_executor.py`)**:
    *   Handles multi-threaded execution of sub-tasks.
    *   Uses Python's `concurrent.futures` or `asyncio.gather` for non-blocking I/O operations.

3.  **Self-Correction (`lib/ers/self_correction.py`)**:
    *   Detects common failures (syntax errors, missing fields).
    *   Automatically feeds the error back to the LLM for a corrected attempt (3 retries max).

4.  **Metrics Collector (`lib/ers/metrics_collector.py`)**:
    *   Tracks latency, token usage, and success rates for every reasoning chain.
    *   Data is used by the `ModelRouter` to adjust future routing decisions.

## 🔄 Execution Flow

1.  **Request**: LLM receives a prompt via `lib/llm.py`.
2.  **Generation**: LLM produces a raw text response.
3.  **Parsers**: ERS attempts to parse YAML/JSON from the response.
4.  **Validation**: Pydantic validates the parsed object.
5.  **Execution**: Validated tool calls are sent to the `parallel_executor`.
6.  **Refinement**: If validation fails, `self_correction` triggers a second pass.

## 🛠️ Usage for Developers

To add a new ERS-protected chain:
```python
from lib.ers.chain import ReasoningChain
from pydantic import BaseModel

class MySchema(BaseModel):
    action: str
    target: str

chain = ReasoningChain(schema=MySchema)
result = await chain.execute(prompt="Do something...")
```
