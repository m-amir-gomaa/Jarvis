# scripts/benchmark_ers.py
import asyncio
import time
from pathlib import Path
from lib.ers.augmentor import ChainAugmentor
from lib.ers.schema import ReasoningChain, ReasoningStep
from lib.security.context import SecurityContext

async def benchmark():
    print("--- ERS Performance Benchmark ---")
    
    # Define a minimal 5-step "null" chain
    steps = [
        ReasoningStep(
            id=f"step_{i}",
            prompt_template="ping",
            model="local/qwen"
        ) for i in range(5)
    ]
    chain = ReasoningChain(id="bench", description="Benchmark chain", steps=steps)
    
    # Mock the model call to exclude inference time
    async def mock_gen(*args, **kwargs):
        return "pong"
    
    augmentor = ChainAugmentor(None, None) # Router and SecurityManager are None
    augmentor.router = type('MockRouter', (), {'generate': mock_gen})
    
    ctx = SecurityContext.default("bench")
    
    start = time.perf_counter()
    await augmentor.run_chain(chain, ctx, {"init": "init"})
    end = time.perf_counter()
    
    total_ms = (end - start) * 1000
    per_step = total_ms / 5
    
    print(f"Total time for 5 steps (overhead): {total_ms:.2f}ms")
    print(f"Average overhead per step: {per_step:.2f}ms")
    
    if per_step < 50:
        print("RESULT: PASSED (< 50ms per step)")
    else:
        print("RESULT: FAILED (> 50ms per step)")

if __name__ == "__main__":
    asyncio.run(benchmark())
