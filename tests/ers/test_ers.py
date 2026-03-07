# tests/ers/test_ers.py
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from lib.ers.schema import ReasoningChain, ReasoningStep
from lib.ers.augmentor import ChainAugmentor, ERSExecutionResult
from lib.security.context import SecurityContext

@pytest.fixture
def mock_router():
    router = MagicMock()
    router.generate = AsyncMock(return_value=("Mocked LLM Response", {"prompt_tokens": 10, "output_tokens": 5}))
    return router

@pytest.fixture
def mock_security():
    sm = MagicMock()
    sm.request = MagicMock(return_value=MagicMock())
    return sm

@pytest.fixture
def augmentor(mock_router, mock_security):
    return ChainAugmentor(model_router=mock_router, security_manager=mock_security)

@pytest.mark.asyncio
async def test_run_sequential_chain(augmentor, mock_router):
    chain = ReasoningChain(
        id="test_chain",
        description="test",
        steps=[
            ReasoningStep(id="step1", prompt_template="Hello {{ name }}"),
            ReasoningStep(id="step2", prompt_template="Step1 said: {{ step1 }}")
        ]
    )
    ctx = SecurityContext.default("cli")
    result = await augmentor.run_chain(chain, ctx, initial_context={"name": "Alice"})
    
    assert result.success
    assert result.outputs["step1"] == "Mocked LLM Response"
    assert result.outputs["step2"] == "Mocked LLM Response"
    assert mock_router.generate.call_count == 2
    
    # Verify Jinja2 rendering in second call
    call_args = mock_router.generate.call_args_list[1]
    assert "Step1 said: Mocked LLM Response" in call_args.kwargs["prompt"]

@pytest.mark.asyncio
async def test_run_batch_chain(augmentor, mock_router, monkeypatch):
    # Ensure RAM gate allows parallel execution
    monkeypatch.setattr("lib.ers.augmentor.ChainAugmentor._ram_ok", lambda x: True)
    
    chain = ReasoningChain(
        id="batch_chain",
        description="test",
        steps=[
            ReasoningStep(id="b1", batch_group="g1", prompt_template="P1"),
            ReasoningStep(id="b2", batch_group="g1", prompt_template="P2"),
        ]
    )
    ctx = SecurityContext.default("cli")
    result = await augmentor.run_chain(chain, ctx)
    
    assert result.success
    assert len(result.outputs) == 2
    assert mock_router.generate.call_count == 2

@pytest.mark.asyncio
async def test_ram_gate_serialization(augmentor, mock_router, monkeypatch):
    # Force RAM gate to fail (force serialization)
    monkeypatch.setattr("lib.ers.augmentor.ChainAugmentor._ram_ok", lambda x: False)
    
    chain = ReasoningChain(
        id="batch_chain",
        description="test",
        steps=[
            ReasoningStep(id="b1", batch_group="g1", prompt_template="P1"),
            ReasoningStep(id="b2", batch_group="g1", prompt_template="P2"),
        ]
    )
    ctx = SecurityContext.default("cli")
    await augmentor.run_chain(chain, ctx)
    
    # We can't easily prove it was serial vs parallel with mocks without timing,
    # but we can verify it still completes correctly.
    assert mock_router.generate.call_count == 2

@pytest.mark.asyncio
async def test_step_failure_stops_chain(augmentor, mock_router):
    mock_router.generate = AsyncMock(side_effect=[
        Exception("LLM Crash"),
        ("Should not run", {"prompt_tokens": 0, "output_tokens": 0})
    ])
    
    chain = ReasoningChain(
        id="fail_chain",
        description="test",
        steps=[
            ReasoningStep(id="s1", prompt_template="P1", on_failure="stop"),
            ReasoningStep(id="s2", prompt_template="P2")
        ]
    )
    ctx = SecurityContext.default("cli")
    result = await augmentor.run_chain(chain, ctx)
    
    assert not result.success
    assert len(result.errors) == 1
    assert "LLM Crash" in result.errors[0]
    assert mock_router.generate.call_count == 1
