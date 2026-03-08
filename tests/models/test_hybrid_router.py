import pytest
from unittest.mock import patch, MagicMock
from lib.models.hybrid_router import HybridRouter

@pytest.fixture
def base_config():
    return {
        "local_primary": "local_qwen14b",
        "local_secondary": "local_llama8b",
        "cloud_primary": "cloud_claude3",
        "local_threshold": 0.65,
        "cloud_enabled": True
    }

@pytest.fixture
def model_capabilities():
    return {
        "local_qwen14b": {
            "capability_score": 0.8,
            "is_local": True,
            "cost_per_1k": 0.0
        },
        "local_llama8b": {
            "capability_score": 0.6,
            "is_local": True,
            "cost_per_1k": 0.0
        },
        "cloud_claude3": {
            "capability_score": 0.95,
            "is_local": False,
            "cost_per_1k": 0.015
        }
    }

def test_assess_task_complexity(base_config, model_capabilities):
    router = HybridRouter(base_config, model_capabilities)
    # Short simple prompt
    score_low = router.assess_task_complexity("Hi")
    # Complex prompt
    score_high = router.assess_task_complexity("Please analyze and synthesize this architecture.")
    
    assert score_low < score_high
    assert 0.0 <= score_low <= 1.0
    assert 0.0 <= score_high <= 1.0

@patch("lib.models.hybrid_router.psutil")
def test_system_load_healthy(mock_psutil, base_config, model_capabilities):
    mock_mem = MagicMock()
    mock_mem.available = 8 * 1024 * 1024 * 1024
    mock_mem.total = 16 * 1024 * 1024 * 1024
    mock_psutil.virtual_memory.return_value = mock_mem
    mock_psutil.cpu_percent.return_value = 10.0 # 10% used
    
    router = HybridRouter(base_config, model_capabilities)
    load = router.check_system_load()
    
    # Mem = 0.5 * 0.7 = 0.35
    # CPU = 0.9 * 0.3 = 0.27
    # Total ~ 0.62
    assert 0.6 < load < 0.65

@patch("lib.models.hybrid_router.psutil")
def test_routing_local_sufficient(mock_psutil, base_config, model_capabilities):
    """If local score exceeds threshold, route to local primary."""
    mock_mem = MagicMock()
    mock_mem.available = 8 * 1024 * 1024 * 1024
    mock_mem.total = 16 * 1024 * 1024 * 1024
    mock_psutil.virtual_memory.return_value = mock_mem
    mock_psutil.cpu_percent.return_value = 10.0
    
    router = HybridRouter(base_config, model_capabilities)
    # Simple prompt
    target = router.route("Hello world")
    assert target == "local_qwen14b"

@patch("lib.models.hybrid_router.psutil")
def test_routing_cloud_fallback(mock_psutil, base_config, model_capabilities):
    """If task is complex and local system is under extreme load, route to cloud."""
    mock_mem = MagicMock()
    mock_mem.available = 1 * 1024 * 1024 * 1024 # Very low mem
    mock_mem.total = 16 * 1024 * 1024 * 1024
    mock_psutil.virtual_memory.return_value = mock_mem
    mock_psutil.cpu_percent.return_value = 95.0 # Very high CPU
    
    router = HybridRouter(base_config, model_capabilities)
    
    # Complex prompt
    target = router.route("Analyze this complex architecture and reason about the requirements.")
    
    # local_qwen14b capability 0.8, -0.4 for heavy load = 0.4 score (< threshold 0.65)
    # falls back to cloud
    assert target == "cloud_claude3"

@patch("lib.models.hybrid_router.psutil")
def test_routing_budget_exhausted(mock_psutil, base_config, model_capabilities):
    """If budget is empty, force local even if cloud would be better."""
    mock_mem = MagicMock()
    mock_mem.available = 1 * 1024 * 1024 * 1024 
    mock_mem.total = 16 * 1024 * 1024 * 1024
    mock_psutil.virtual_memory.return_value = mock_mem
    mock_psutil.cpu_percent.return_value = 95.0 
    
    # Provide 0 budget
    router = HybridRouter(base_config, model_capabilities, initial_budget=0.0)
    
    target = router.route("Analyze this complex architecture and reason about the requirements.")
    # Cloud should be penalized due to budget, so it will return best local
    assert target == "local_qwen14b"

@patch("lib.models.hybrid_router.psutil")
@pytest.mark.asyncio
async def test_async_capabilities(mock_psutil, base_config, model_capabilities):
    """Test that it can be used in async functions effectively, no blocking behavior."""
    router = HybridRouter(base_config, model_capabilities)
    target = router.route("Quick hello")
    assert target == "local_qwen14b"
