# tests/ers/test_chain_loader.py
import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from lib.ers.chain import ChainLoader, ChainValidationError
from lib.ers.schema import ReasoningChain
from lib.ers.augmentor import ChainAugmentor
from lib.security.context import SecurityContext


def test_load_valid_chain(tmp_path):
    f = tmp_path / "simple.yaml"
    f.write_text("""
id: simple
description: A simple test chain
steps:
  - id: s1
    prompt_template: "Hello {{ name }}"
    model_alias: chat
""")
    loader = ChainLoader(tmp_path)
    chain = loader.load_file(f)
    assert isinstance(chain, ReasoningChain)
    assert chain.id == "simple"
    assert chain.steps[0].prompt_template == "Hello {{ name }}"
    assert chain.steps[0].model_alias == "chat"


def test_rejects_missing_id(tmp_path):
    f = tmp_path / "bad.yaml"
    f.write_text("""
description: Missing id
steps:
  - id: s1
    prompt_template: "hi"
    model_alias: chat
""")
    with pytest.raises(ChainValidationError, match="missing required fields"):
        ChainLoader(tmp_path).load_file(f)


def test_rejects_empty_steps(tmp_path):
    f = tmp_path / "bad.yaml"
    f.write_text("id: x\ndescription: y\nsteps: []\n")
    with pytest.raises(ChainValidationError):
        ChainLoader(tmp_path).load_file(f)


def test_rejects_invalid_jinja2(tmp_path):
    f = tmp_path / "bad_tpl.yaml"
    f.write_text("""
id: broken
description: bad template
steps:
  - id: s1
    prompt_template: "{{ unclosed"
    model_alias: chat
""")
    with pytest.raises(ChainValidationError, match="invalid Jinja2"):
        ChainLoader(tmp_path).load_file(f)


def test_load_all_skips_invalid(tmp_path):
    (tmp_path / "good.yaml").write_text("""
id: good
description: valid
steps:
  - id: s1
    prompt_template: "hi"
    model_alias: fast
""")
    (tmp_path / "bad.yaml").write_text("not: a: chain")
    registry = ChainLoader(tmp_path).load_all()
    assert "good" in registry
    assert len(registry) == 1


@pytest.mark.asyncio
async def test_loaded_chain_compatible_with_augmentor(tmp_path):
    """End-to-end: load YAML → run through ChainAugmentor."""
    f = tmp_path / "compat.yaml"
    f.write_text("""
id: compat
description: compatibility check
steps:
  - id: step1
    prompt_template: "Research {{ topic }}"
    model_alias: chat
    output_key: research
  - id: step2
    prompt_template: "Summarize: {{ research }}"
    model_alias: fast
    output_key: summary
""")
    loader = ChainLoader(tmp_path)
    chain  = loader.load_file(f)

    router = MagicMock()
    router.generate = AsyncMock(
        return_value=("mocked output", {"prompt_tokens": 5, "output_tokens": 3})
    )
    sm = MagicMock()
    sm.request = MagicMock(return_value=MagicMock())
    aug = ChainAugmentor(model_router=router, security_manager=sm)
    ctx = SecurityContext.default("cli")

    result = await aug.run_chain(chain, ctx, initial_context={"topic": "NixOS"})
    assert result.success, f"Chain failed: {result.errors}"

    # Verify step 2 received step 1's text, not a tuple
    call2 = router.generate.call_args_list[1]
    prompt2 = call2.kwargs["prompt"]
    assert "mocked output" in prompt2
    assert "prompt_tokens" not in prompt2
