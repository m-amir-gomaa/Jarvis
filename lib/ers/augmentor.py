# lib/ers/augmentor.py
from __future__ import annotations
import asyncio, logging, psutil
from datetime import timezone
from typing import Any
from jinja2 import Template, Environment, StrictUndefined

from pydantic import BaseModel
from .schema import ReasoningChain, ReasoningStep
from ..security.context import SecurityContext, CapabilityGrant
from ..security.grants import CapabilityRequest

log = logging.getLogger("jarvis.ers")

# RAM gate: Serialized if available memory < this threshold (MB)
RAM_GATE_MB = 1024 

class ERSExecutionResult(BaseModel):
    chain_id: str
    success:  bool
    outputs:  dict[str, str | None]
    errors:   list[str]

class ChainAugmentor:
    def __init__(self, model_router, security_manager):
        self.router = model_router
        self.security = security_manager
        self.env = Environment(undefined=StrictUndefined)

    async def run_chain(self, chain: ReasoningChain, ctx: SecurityContext, initial_context: dict[str, Any] = None) -> ERSExecutionResult:
        # Require reasoning:elevated capability
        try:
            grant = self.security.request(ctx, CapabilityRequest(
                capability="reasoning:elevated",
                reason=f"Execute ERS chain: {chain.id}",
                scope="task"
            ))
        except Exception as e:
            return ERSExecutionResult(chain_id=chain.id, success=False, outputs={}, errors=[str(e)])

        execution_context = initial_context or {}
        outputs = {}
        errors = []
        
        # Group steps by execution blocks (sequential or batch)
        blocks = self._plan_blocks(chain.steps)
        
        for block in blocks:
            if len(block) == 1 and block[0].batch_group is None:
                # Sequential step
                res = await self._run_step(block[0], ctx, execution_context)
                if res["error"]:
                    errors.append(res["error"])
                    if block[0].on_failure == "stop":
                        return ERSExecutionResult(chain_id=chain.id, success=False, outputs=outputs, errors=errors)
                else:
                    outputs[res["key"]] = res["output"]
                    execution_context[res["key"]] = res["output"]
            else:
                # Batch group
                batch_res = await self._run_batch(block, ctx, execution_context)
                batch_halt = False
                for i, res in enumerate(batch_res):
                    step = block[i]
                    if res["error"]:
                        errors.append(f"Step {step.id} failed: {res['error']}")
                        if step.on_failure == "stop":
                            batch_halt = True
                    if res["output"]:
                        outputs[res["key"]] = res["output"]
                        execution_context[res["key"]] = res["output"]
                
                if batch_halt:
                    return ERSExecutionResult(chain_id=chain.id, success=False, outputs=outputs, errors=errors)
                
        return ERSExecutionResult(chain_id=chain.id, success=True, outputs=outputs, errors=errors)

    def _plan_blocks(self, steps: list[ReasoningStep]) -> list[list[ReasoningStep]]:
        blocks = []
        current_batch_group = None
        current_block = []
        
        for step in steps:
            if step.batch_group:
                if step.batch_group == current_batch_group:
                    current_block.append(step)
                else:
                    if current_block:
                        blocks.append(current_block)
                    current_block = [step]
                    current_batch_group = step.batch_group
            else:
                if current_block:
                    blocks.append(current_block)
                blocks.append([step])
                current_block = []
                current_batch_group = None
        if current_block:
            blocks.append(current_block)
        return blocks

    async def _run_step(self, step: ReasoningStep, ctx: SecurityContext, exec_ctx: dict[str, Any]) -> dict[str, str | None]:
        key = step.output_key or step.id
        # Isolated child context — created outside try so finally can reference it
        child_ctx = ctx.child_context(f"ers:{step.id}", trust_ceiling=ctx.trust_level)
        try:
            # Render prompt with Jinja2
            tpl = self.env.from_string(step.prompt_template)
            prompt = tpl.render(**exec_ctx)
            
            # Request model capability via router
            response = await self.router.generate(
                model_alias=step.model_alias,
                prompt=prompt,
                stop=step.stop_sequences,
                max_tokens=step.max_tokens,
                ctx=child_ctx
            )
            return {"key": key, "output": response[0], "error": None}
        except Exception as e:
            import traceback
            err_str = traceback.format_exc()
            log.error(f"Step {step.id} failed: {err_str}")
            print(f"Step {step.id} failed: {err_str}")
            return {"key": key, "output": None, "error": str(repr(e))}
        finally:
            # Revoke all task-scoped grants on the step child context.
            # Produces audit trail for step-level capability lifecycle.
            revoked = child_ctx.revoke_task_grants()
            if revoked:
                log.debug(f"Step {step.id}: revoked {revoked} task grant(s) from child context")

    def _ram_ok(self) -> bool:
        mem = psutil.virtual_memory()
        return (mem.available / (1024 * 1024)) > RAM_GATE_MB

    async def _run_batch(self, steps: list[ReasoningStep], ctx: SecurityContext, exec_ctx: dict[str, Any]) -> list[dict[str, str | None]]:
        if not self._ram_ok():
            log.warning("[ERS] RAM low, serializing batch steps")
            results = []
            for s in steps:
                results.append(await self._run_step(s, ctx, exec_ctx))
            return results
        
        # Run in parallel
        return list(await asyncio.gather(*[self._run_step(s, ctx, exec_ctx) for s in steps]))
