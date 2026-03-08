# lib/ers/parallel_executor.py
import asyncio
import logging
from typing import Any
from lib.ers.yaml_schema import Step, ToolChainSchema
from lib.ers.adaptive_router import AdaptiveRouter

logger = logging.getLogger(__name__)

class ChainContext:
    """Thread-safe state management for tool chains."""
    def __init__(self, initial_state: dict[str, Any] | None = None) -> None:
        self.state: dict[str, Any] = initial_state or {}
        self._lock = asyncio.Lock()
        
    async def update(self, new_data: dict[str, Any]) -> None:
        async with self._lock:
            self.state.update(new_data)
            
    async def get(self, key: str, default: Any = None) -> Any:
        async with self._lock:
            return self.state.get(key, default)
            
    async def get_all(self) -> dict[str, Any]:
        async with self._lock:
            return self.state.copy()

class ParallelExecutor:
    """Executes ERS chains, parallelizing steps grouped by 'parallel_group'."""
    
    def __init__(self, router: AdaptiveRouter):
        self.router = router
        
    async def execute_chain(
        self,
        execution_id: str,
        chain: ToolChainSchema,
        initial_inputs: dict[str, Any],
        group_failure_policy: str = "abort" # 'abort' or 'continue'
    ) -> tuple[bool, dict[str, Any]]:
        
        context = ChainContext(initial_inputs)
        
        # Batch adjacent steps with the same parallel_group
        step_batches: list[tuple[str | None, list[Step]]] = []
        current_batch: list[Step] = []
        current_group: str | None = None
        
        for step in chain.steps:
            if step.parallel_group:
                if current_group == step.parallel_group:
                    current_batch.append(step)
                else:
                    if current_batch:
                        step_batches.append((current_group, current_batch))
                    current_group = step.parallel_group
                    current_batch = [step]
            else:
                if current_batch:
                    step_batches.append((current_group, current_batch))
                    current_batch = []
                    current_group = None
                step_batches.append((None, [step]))
                
        if current_batch:
            step_batches.append((current_group, current_batch))
            
        for group_id, batch in step_batches:
            if group_id:
                success = await self._execute_parallel_batch(execution_id, batch, context, group_failure_policy)
                if not success and group_failure_policy == "abort":
                    return False, await context.get_all()
            else:
                step = batch[0]
                success = await self._execute_single_step(execution_id, step, context)
                if not success:
                    return False, await context.get_all()
                    
        return True, await context.get_all()
        
    async def _execute_parallel_batch(self, execution_id: str, batch: list[Step], context: ChainContext, policy: str) -> bool:
        async def run_step(step: Step) -> bool:
            return await self._execute_single_step(execution_id, step, context)
            
        results = await asyncio.gather(*(run_step(s) for s in batch), return_exceptions=True)
        
        failures = sum(1 for r in results if isinstance(r, Exception) or r is False)
        
        if failures > 0 and policy == "abort":
            return False
            
        return True
        
    async def _execute_single_step(self, execution_id: str, step: Step, context: ChainContext) -> bool:
        current_state = await context.get_all()
        # Resolve inputs: if step defines static inputs in YAML, merge them with current context state.
        inputs = current_state.copy()
        if step.inputs:
            inputs.update(step.inputs)
            
        success, updates_or_error = await self.router.route_step(
            execution_id=execution_id,
            step=step,
            inputs=inputs
        )
        
        if success:
            await context.update(updates_or_error)
            return True
            
        logger.error(f"Step {step.id} failed: {updates_or_error}")
        return False
