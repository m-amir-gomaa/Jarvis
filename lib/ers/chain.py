# lib/ers/chain.py
"""
ChainLoader: loads ReasoningChain definitions from YAML files.
Produces ReasoningChain/ReasoningStep objects (lib.ers.schema) that are
directly compatible with ChainAugmentor.run_chain().
"""
from __future__ import annotations
import logging
from pathlib import Path
import yaml
from pydantic import ValidationError
from .schema import ReasoningChain, ReasoningStep  # noqa: F401 re-exported

log = logging.getLogger("jarvis.ers.chain")


class ChainValidationError(Exception):
    """Raised when a YAML chain fails schema validation at load time."""
    pass


class ChainLoader:
    """
    Loads ReasoningChain definitions from YAML files.
    Validates at load time — malformed chains raise ChainValidationError
    immediately rather than failing silently inside execute().
    """

    def __init__(self, chains_dir: Path | str | None = None):
        if chains_dir is None:
            import os
            jarvis_root = Path(os.environ.get(
                "JARVIS_ROOT", Path(__file__).resolve().parent.parent.parent
            ))
            chains_dir = jarvis_root / "chains"
        self.chains_dir = Path(chains_dir)
        self._registry: dict[str, ReasoningChain] = {}

    # ── Public API ────────────────────────────────────────────────────────────

    def load_all(self) -> dict[str, ReasoningChain]:
        """Load every .yaml in chains_dir recursively.
        Invalid files are skipped with an error log.
        Returns {chain_id: ReasoningChain}."""
        if not self.chains_dir.exists():
            log.warning(f"Chains directory not found: {self.chains_dir}")
            return {}
        for path in sorted(self.chains_dir.rglob("*.yaml")):
            try:
                chain = self.load_file(path)
                self._registry[chain.id] = chain
                log.info(f"Loaded chain '{chain.id}' from {path.name}")
            except ChainValidationError as e:
                log.error(f"Skipping invalid chain {path.name}: {e}")
            except Exception as e:
                log.error(f"Failed to load {path.name}: {e}")
        return dict(self._registry)

    def load_file(self, path: Path | str) -> ReasoningChain:
        """Load and validate a single YAML chain file."""
        path = Path(path)
        try:
            raw = yaml.safe_load(path.read_text())
        except yaml.YAMLError as e:
            raise ChainValidationError(f"YAML parse error in {path.name}: {e}") from e
        return self._validate(raw, source=path.name)

    def get(self, chain_id: str) -> ReasoningChain | None:
        """Return a previously loaded chain by id, or None."""
        return self._registry.get(chain_id)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _validate(self, raw: dict, source: str = "<unknown>") -> ReasoningChain:
        if not isinstance(raw, dict):
            raise ChainValidationError(
                f"{source}: top-level must be a mapping, got {type(raw).__name__}"
            )
        required = {"id", "description", "steps"}
        missing = required - raw.keys()
        if missing:
            raise ChainValidationError(
                f"{source}: missing required fields: {missing}"
            )
        if not isinstance(raw.get("steps"), list) or len(raw["steps"]) == 0:
            raise ChainValidationError(
                f"{source}: 'steps' must be a non-empty list"
            )

        # Validate Jinja2 syntax per-step before Pydantic (better error messages)
        from jinja2 import Environment, TemplateSyntaxError
        env = Environment()
        for i, step in enumerate(raw["steps"]):
            tpl = step.get("prompt_template", "")
            try:
                env.parse(tpl)
            except TemplateSyntaxError as e:
                step_id = step.get("id", f"step[{i}]")
                raise ChainValidationError(
                    f"{source}: step '{step_id}' has invalid Jinja2 template: {e}"
                ) from e

        try:
            return ReasoningChain.model_validate(raw)
        except ValidationError as e:
            raise ChainValidationError(
                f"{source}: schema validation failed:\n{e}"
            ) from e
