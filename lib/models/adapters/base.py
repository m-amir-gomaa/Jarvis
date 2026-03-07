# lib/models/adapters/base.py
from abc import ABC, abstractmethod
from typing import Any

class ModelAdapter(ABC):
    provider_name: str = ""

    @abstractmethod
    async def generate(self, model: str, prompt: str, stop: list[str] | None = None, max_tokens: int = 1024, **kwargs) -> str:
        """Generate text from the model. Returns the response string."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the provider is configured and reachable."""
        ...
