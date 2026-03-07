# lib/ers/seed_loader.py
"""
PromptSeedLoader: wraps an existing prompt string in an ERS execution envelope.

The seed prompt text is preserved byte-for-byte as the `seed` key in the initial
execution context. Chain steps reference it via {{ seed }} in their prompt_template.

Usage:
    loader = PromptSeedLoader()
    initial_ctx = loader.wrap("Explain how Nix flakes work")
    result = await augmentor.run_chain(chain, ctx, initial_context=initial_ctx)

The seed text is never modified or summarised. ERS chain steps augment the result —
they do not replace the original prompt.
"""
from __future__ import annotations
import hashlib
import logging
from typing import Any

log = logging.getLogger("jarvis.ers.seed_loader")

# Key under which the seed prompt is stored in the execution context.
# Chain YAML templates reference it as {{ seed }}.
SEED_KEY = "seed"


class PromptSeedLoader:
    """
    Wraps a plain text prompt string into an ERS initial execution context.

    The seed is stored under the key 'seed' and is byte-for-byte unchanged.
    A content hash is stored under 'seed_hash' for audit / deduplication.
    """

    def __init__(self, seed_key: str = SEED_KEY):
        self.seed_key = seed_key

    def wrap(self, prompt: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Return an initial_context dict suitable for ChainAugmentor.run_chain().

        Args:
            prompt: The raw prompt string to use as the ERS seed. Preserved exactly.
            extra:  Any additional key/value pairs to inject into the execution context
                    alongside the seed. Keys must not conflict with 'seed' or 'seed_hash'.

        Returns:
            dict with at minimum: {seed_key: prompt, 'seed_hash': sha256_hex}
        """
        if not isinstance(prompt, str):
            raise TypeError(f"seed prompt must be str, got {type(prompt).__name__}")
        if not prompt.strip():
            raise ValueError("seed prompt must not be empty or whitespace-only")

        seed_hash = hashlib.sha256(prompt.encode()).hexdigest()

        ctx: dict[str, Any] = {
            self.seed_key: prompt,
            "seed_hash": seed_hash,
        }

        if extra:
            conflicts = set(extra.keys()) & {self.seed_key, "seed_hash"}
            if conflicts:
                raise ValueError(
                    f"extra keys conflict with reserved seed context keys: {conflicts}"
                )
            ctx.update(extra)

        log.debug(
            f"PromptSeedLoader.wrap(): seed_hash={seed_hash[:12]}… "
            f"length={len(prompt)} chars"
        )
        return ctx

    def unwrap(self, execution_context: dict[str, Any]) -> str | None:
        """
        Extract the original seed prompt from an execution context dict.
        Returns None if the seed key is not present.
        """
        return execution_context.get(self.seed_key)
