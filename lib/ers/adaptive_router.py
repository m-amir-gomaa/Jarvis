# lib/ers/adaptive_router.py
import logging
from typing import Any, Callable, Awaitable
from lib.ers.yaml_schema import Step
from lib.ers.self_correction import SelfCorrectionLoop

logger = logging.getLogger(__name__)

class ToolRegistry:
    """Semantic lookup registry for tools, supporting substitution."""
    def __init__(self) -> None:
        self.tools: dict[str, dict[str, Any]] = {}
        
    def register_tool(self, name: str, func: Callable[..., Awaitable[Any]], description: str, tags: list[str]) -> None:
        self.tools[name] = {"func": func, "description": description, "tags": tags}
        
    def find_substitute(self, failed_tool_name: str) -> str | None:
        """Semantic lookup: finds a tool sharing at least one tag."""
        if failed_tool_name not in self.tools:
            return None
        
        failed_tags = set(self.tools[failed_tool_name]["tags"])
        for name, info in self.tools.items():
            if name != failed_tool_name and failed_tags.intersection(info["tags"]):
                return name
        return None

class AdaptiveRouter:
    """Wraps chain execution and routes dynamically around failures."""
    
    def __init__(self, tool_registry: ToolRegistry, self_correction: SelfCorrectionLoop | None = None):
        self.registry = tool_registry
        self.self_correction = self_correction
        
    async def _execute_tool(self, name: str, inputs: dict[str, Any]) -> tuple[bool, Any]:
        try:
            if name in self.registry.tools:
                func = self.registry.tools[name]["func"]
                res = await func(**inputs)
                return True, res
            else:
                return False, f"Tool '{name}' not found in registry"
        except Exception as e:
            logger.error(f"Tool {name} execution failed: {e}")
            return False, str(e)
            
    def _map_outputs(self, step: Step, result: Any) -> dict[str, Any]:
        """Maps an un-structured tool result to the context dictionary keys."""
        context = {}
        if isinstance(step.outputs, list) and step.outputs:
            # simple mapping: first key gets the whole result
            key = step.outputs[0]
            context[key] = result
        elif isinstance(step.outputs, dict):
             # Dict mapping scenario, simple key matching
             for out_key, in_key in step.outputs.items():
                 if isinstance(result, dict) and in_key in result:
                     context[out_key] = result[in_key]
                 else:
                     context[out_key] = result # fallback
        return context

    async def route_step(
        self,
        execution_id: str,
        step: Step,
        inputs: dict[str, Any],
        llm_caller: Callable[[str], Awaitable[tuple[str, dict[str, Any], float]]] | None = None
    ) -> tuple[bool, dict[str, Any]]:
        """
        Executes a step with dynamic routing based on on_failure policies.
        Returns (success, new_context_updates_or_error_details).
        """
        tool_name = step.tool
        success, result = await self._execute_tool(tool_name, inputs)
        
        if success:
            return True, self._map_outputs(step, result)
            
        policy = step.on_failure
        
        if policy == "retry":
            for _ in range(3):
                success, result = await self._execute_tool(tool_name, inputs)
                if success:
                    return True, self._map_outputs(step, result)
            return False, {"error": f"Failed after retries: {result}"}
            
        elif policy == "substitute":
            sub_tool = self.registry.find_substitute(tool_name)
            if sub_tool:
                success, result = await self._execute_tool(sub_tool, inputs)
                if success:
                    return True, self._map_outputs(step, result)
            return False, {"error": "Substitute completely failed or not found"}
            
        elif policy == "correct":
            if not self.self_correction or not llm_caller:
                return False, {"error": "Self-correction not configured but policy is 'correct'."}
                
            attempt = await self.self_correction.run_correction(
                execution_id=execution_id,
                step_id=step.id,
                tool_name=tool_name,
                failed_inputs=inputs,
                error_message=result,
                llm_caller=llm_caller,
                tool_executor=self._execute_tool
            )
            if attempt.success:
                return True, self._map_outputs(step, attempt.tool_result)
            return False, {"error": f"Correction failed: {attempt.diagnostics}"}
            
        elif policy == "skip":
            return True, {"warning": f"Skipped step {step.id} due to failure: {result}"}
            
        # Default abort
        return False, {"error": f"Step aborted: {result}"}
