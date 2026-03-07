# lib/ers/access_protocol.py
"""
ERSAccessProtocol: an abstraction for capability requests during ERS steps.

Allows ERS reasoning steps to declare their own security requirements
before execution. The augmentor uses this protocol to ensure the held
SecurityContext has the necessary grants before calling the model router.
"""
from __future__ import annotations
from typing import Any, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from ..security.context import SecurityContext
    from ..security.grants import CapabilityGrantManager, CapabilityRequest

log = logging.getLogger("jarvis.ers.access")

class ERSAccessProtocol:
    """
    Handles security negotiation for ERS reasoning steps.
    """
    def __init__(self, security_manager: CapabilityGrantManager):
        self.sm = security_manager

    def negotiate(self, ctx: SecurityContext, requests: list[CapabilityRequest]) -> bool:
        """
        Request a list of capabilities for the given context.
        Returns True if all were granted, False otherwise.
        """
        from ..security.exceptions import CapabilityDenied, TrustLevelError, CapabilityPending
        
        for req in requests:
            try:
                self.sm.request(ctx, req)
            except (CapabilityDenied, TrustLevelError, CapabilityPending) as e:
                log.warning(f"Protocol negotiation failed for {req.capability}: {e}")
                return False
            except Exception as e:
                log.error(f"Unexpected error during protocol negotiation: {e}")
                return False
        return True

    def check_step_requirements(self, ctx: SecurityContext, step_id: str, requirements: list[str]) -> bool:
        """
        Directly check if the context holds a list of capabilities.
        Does not request new ones.
        """
        for cap in requirements:
            if not ctx.has(cap):
                log.warning(f"Step {step_id}: missing required capability '{cap}'")
                return False
        return True
