import os
import yaml
import pytest
from lib.models.prompt_refiner import PromptRefiner

@pytest.fixture
def temp_prompts_dir(tmp_path):
    """Fixture to create a temporary directory with prompt templates."""
    d = tmp_path / "prompts"
    d.mkdir()
    
    # Create a dummy yaml
    templates = {
        "code_review": "Review the following code:\n{code}",
        "summarize": "Summarize this: {text}"
    }
    
    p = d / "default.yaml"
    with open(p, "w") as f:
        yaml.dump(templates, f)
        
    return str(d)

def test_load_templates(temp_prompts_dir):
    refiner = PromptRefiner(templates_dir=temp_prompts_dir)
    assert "code_review" in refiner.templates
    assert refiner.templates["code_review"] == "Review the following code:\n{code}"

def test_format_prompt_claude(temp_prompts_dir):
    refiner = PromptRefiner(templates_dir=temp_prompts_dir)
    
    context = {"code": "print('hello')"}
    result = refiner.format_prompt("code_review", context, "anthropic")
    
    assert "<prompt>" in result
    assert "</prompt>" in result
    assert "print('hello')" in result

def test_format_prompt_local(temp_prompts_dir):
    refiner = PromptRefiner(templates_dir=temp_prompts_dir)
    
    context = {"code": "print('hello')"}
    result = refiner.format_prompt("code_review", context, "ollama")
    
    assert "### Instruction:" in result
    assert "### Response:" in result
    assert "print('hello')" in result

def test_missing_context_fallback(temp_prompts_dir):
    refiner = PromptRefiner(templates_dir=temp_prompts_dir)
    
    # Missing {code} context
    result = refiner.format_prompt("code_review", {"text": "dummy"}, "generic")
    
    # It should fallback gracefully without crashing
    assert "Review the following code:" in result

def test_dry_run_metrics(temp_prompts_dir):
    refiner = PromptRefiner(templates_dir=temp_prompts_dir)
    
    # Normal run increments metric
    refiner.format_prompt("summarize", {"text": "abc"}, "generic")
    assert refiner.metrics["summarize"]["invocations"] == 1
    
    # Dry run does not increment metric
    refiner.format_prompt("summarize", {"text": "def"}, "generic", dry_run=True)
    assert refiner.metrics["summarize"]["invocations"] == 1

def test_high_correction_flag(temp_prompts_dir):
    refiner = PromptRefiner(templates_dir=temp_prompts_dir)
    
    # Simulate 10 invocations and 4 corrections ( > 0.3 threshold)
    refiner.metrics["code_review"] = {"invocations": 10, "corrections": 4}
    
    # Simulate 10 invocations and 1 correction ( < 0.3 threshold)
    refiner.metrics["summarize"] = {"invocations": 10, "corrections": 1}
    
    high_corr = refiner.get_high_correction_templates()
    
    assert "code_review" in high_corr
    assert "summarize" not in high_corr
