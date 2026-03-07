# lib/security/exceptions.py

class CapabilityDenied(Exception):
    """Raised when an agent tries to use a capability it does not hold."""
    def __init__(self, capability: str, agent_id: str):
        self.capability = capability
        self.agent_id = agent_id
        super().__init__(
            f"Agent '{agent_id}' does not hold capability '{capability}'"
        )

class TrustLevelError(Exception):
    """Raised when a trust-level assertion fails (e.g., clone > parent)."""
    pass

class CapabilityExpired(CapabilityDenied):
    """Raised when a held capability has passed its expiry time."""
    pass

class CapabilityPending(Exception):
    """Raised when a capability request requires OOB (out-of-band) user approval."""
    def __init__(self, capability: str, agent_id: str, pending_id: str):
        self.capability  = capability
        self.agent_id    = agent_id
        self.pending_id  = pending_id
        super().__init__(
            f"Capability '{capability}' for agent '{agent_id}' awaiting OOB approval. "
            f"Run: jarvis approve {pending_id}"
        )
