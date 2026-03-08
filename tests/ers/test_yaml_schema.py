import pytest
from pydantic import ValidationError
from lib.ers.yaml_schema import ToolChainSchema, Step, Conditional

def test_tool_chain_schema_valid() -> None:
    data = {
        "id": "test_chain",
        "description": "A test chain",
        "steps": [
            {
                "id": "step1",
                "tool": "calculator",
                "inputs": {"expression": "2 + 2"},
                "outputs": ["result"],
                "on_failure": "retry"
            }
        ],
        "metrics": {"enabled": False}
    }
    chain = ToolChainSchema(**data)
    assert chain.id == "test_chain"
    assert len(chain.steps) == 1
    assert chain.steps[0].id == "step1"
    assert chain.steps[0].tool == "calculator"
    assert chain.steps[0].on_failure == "retry"
    assert chain.metrics.enabled is False

def test_tool_chain_schema_invalid() -> None:
    # Missing required id
    data = {"description": "test"}
    with pytest.raises(ValidationError):
        ToolChainSchema(**data) # type: ignore
        
    # Invalid on_failure literal
    data2 = {
        "id": "test2",
        "steps": [
            {
                "id": "step1",
                "tool": "calc",
                "on_failure": "invalid_policy"
            }
        ]
    }
    with pytest.raises(ValidationError):
        ToolChainSchema(**data2) # type: ignore

def test_step_conditionals() -> None:
    step = Step(
        id="cond_step",
        tool="check_weather",
        conditionals=[
            {"condition": "result == 'rain'", "on_true": "bring_umbrella"} # type: ignore
        ]
    )
    assert len(step.conditionals) == 1
    assert step.conditionals[0].condition == "result == 'rain'"
    assert step.conditionals[0].on_true == "bring_umbrella"
    assert step.conditionals[0].on_false is None
