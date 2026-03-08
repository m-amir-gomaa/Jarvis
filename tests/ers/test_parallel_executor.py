import pytest
import asyncio
import time
from typing import Any
from lib.ers.yaml_schema import ToolChainSchema, Step
from lib.ers.adaptive_router import ToolRegistry, AdaptiveRouter
from lib.ers.parallel_executor import ParallelExecutor, ChainContext

@pytest.fixture
def mock_router() -> AdaptiveRouter:
    reg = ToolRegistry()
    
    async def slow_fetch(item: str) -> dict[str, str]:
        await asyncio.sleep(0.1)
        return {"data": f"fetched_{item}"}
        
    async def fail_fetch(item: str) -> dict[str, str]:
        await asyncio.sleep(0.1)
        raise ValueError("Simulated network failure")
        
    reg.register_tool("slow_fetch", slow_fetch, "Fetches slowly", ["fetch"])
    reg.register_tool("fail_fetch", fail_fetch, "Always fails", ["fetch"])
    return AdaptiveRouter(reg)

@pytest.mark.asyncio
async def test_chain_context() -> None:
    ctx = ChainContext({"initial": 1})
    
    async def modifier(k: str, v: int) -> None:
        await ctx.update({k: v})
        
    await asyncio.gather(
        modifier("a", 2),
        modifier("b", 3),
        modifier("c", 4)
    )
    
    state = await ctx.get_all()
    assert state == {"initial": 1, "a": 2, "b": 3, "c": 4}

@pytest.mark.asyncio
async def test_parallel_execution(mock_router: AdaptiveRouter) -> None:
    executor = ParallelExecutor(mock_router)
    
    step1 = Step(id="s1", tool="slow_fetch", parallel_group="group1", inputs={"item": "apple"}, outputs=["result_1"])
    step2 = Step(id="s2", tool="slow_fetch", parallel_group="group1", inputs={"item": "banana"}, outputs=["result_2"])
    
    chain = ToolChainSchema(
        id="test_chain",
        steps=[step1, step2]
    )
    
    start = time.time()
    success, final_state = await executor.execute_chain("exec1", chain, initial_inputs={})
    end = time.time()
    
    assert success is True
    assert "result_1" in final_state
    assert "result_2" in final_state
    assert final_state["result_1"] == {"data": "fetched_apple"}
    assert final_state["result_2"] == {"data": "fetched_banana"}
    
    # Should take ~0.1s total due to parallel execution, not ~0.2s
    assert end - start < 0.15

@pytest.mark.asyncio
async def test_parallel_group_failure_policy(mock_router: AdaptiveRouter) -> None:
    executor = ParallelExecutor(mock_router)
    
    # s3 fails and aborts, s4 runs but group fails overall
    step3 = Step(id="s3", tool="fail_fetch", parallel_group="g2", inputs={"item": "bad"}, outputs=["result_3"])
    step4 = Step(id="s4", tool="slow_fetch", parallel_group="g2", inputs={"item": "good"}, outputs=["result_4"])
    
    chain = ToolChainSchema(id="fail_chain", steps=[step3, step4])
    
    success, final_state = await executor.execute_chain("exec2", chain, {}, group_failure_policy="abort")
    assert success is False
    # If it was parallel, step4 might have finished or might not have before failure registered, 
    # but the overall success is False.
