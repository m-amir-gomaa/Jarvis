# lib/ers/self_correction.py
import time
from typing import Any, Callable, Awaitable
from pydantic import BaseModel
from lib.ers.metrics_collector import MetricsCollector

class CorrectionAttempt(BaseModel):
    """Result of a single attempt to self-correct a failed tool call."""
    attempt_number: int
    diagnostics: str
    corrected_inputs: dict[str, Any]
    score: float
    success: bool
    tool_result: Any | None = None

class SelfCorrectionLoop:
    """Autonomous self-correction loop when an ERS step fails."""
    
    def __init__(self, metrics_collector: MetricsCollector, max_retries: int = 3):
        self.metrics_collector = metrics_collector
        self.max_retries = max_retries
        
    def _build_meta_prompt(self, tool_name: str, failed_inputs: dict[str, Any], error_message: str) -> str:
        """Constructs the meta-prompt for the LLM to diagnose and correct the error."""
        return f"""You are a self-correction reasoning module.
The tool '{tool_name}' failed with the following error:
{error_message}

The inputs provided were:
{failed_inputs}

Analyze the error, output diagnostics, and provide the corrected inputs for the tool. Use a scale from 0.0 to 1.0 to score your confidence in the fix.
"""

    async def run_correction(
        self,
        execution_id: str,
        step_id: str,
        tool_name: str,
        failed_inputs: dict[str, Any],
        error_message: str,
        llm_caller: Callable[[str], Awaitable[tuple[str, dict[str, Any], float]]],
        tool_executor: Callable[[str, dict[str, Any]], Awaitable[tuple[bool, str]]]
    ) -> CorrectionAttempt:
        """
        Run the self-correction loop up to max_retries times.
        llm_caller: Takes the meta-prompt and returns (diagnostics, new_inputs, score).
        tool_executor: Takes (tool_name, inputs) and returns (is_success, result_or_error_msg).
        """
        attempts = 0
        current_inputs = failed_inputs.copy()
        last_error = error_message
        diff_logs = []
        score = 0.0
        diagnostics = ""
        
        while attempts < self.max_retries:
            attempts += 1
            start_time = time.time()
            
            prompt = self._build_meta_prompt(tool_name, current_inputs, last_error)
            
            # Call LLM to diagnose and correct
            diagnostics, new_inputs, score = await llm_caller(prompt)
            
            diff_logs.append({
                "attempt": attempts,
                "diagnostics": diagnostics,
                "old_inputs": current_inputs,
                "new_inputs": new_inputs,
                "score": score
            })
            
            current_inputs = new_inputs
            
            # Execute tool with corrected inputs
            success, result_or_error = await tool_executor(tool_name, current_inputs)
            latency = time.time() - start_time
            
            if success:
                # Successfully corrected
                await self.metrics_collector.log_step(
                    execution_id=execution_id,
                    step_id=f"{step_id}_correction_success",
                    tool=tool_name,
                    start_time=start_time,
                    end_time=start_time + latency,
                    status="corrected",
                    correction_attempts=attempts,
                    diffs=diff_logs
                )
                return CorrectionAttempt(
                    attempt_number=attempts,
                    diagnostics=diagnostics,
                    corrected_inputs=current_inputs,
                    score=score,
                    success=True,
                    tool_result=result_or_error
                )
            
            # Try again
            last_error = result_or_error
            
        # Failed completely after max retries
        await self.metrics_collector.log_step(
            execution_id=execution_id,
            step_id=f"{step_id}_correction_failed",
            tool=tool_name,
            start_time=time.time(),
            end_time=time.time() + 0.01,
            status="correction_failed",
            correction_attempts=attempts,
            diffs=diff_logs
        )
        return CorrectionAttempt(
            attempt_number=attempts,
            diagnostics=f"Exceeded max retries. Last diag: {diagnostics}",
            corrected_inputs=current_inputs,
            score=score,
            success=False,
            tool_result=last_error
        )
