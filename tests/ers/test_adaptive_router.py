import pytest
from lib.ers.yaml_schema import Step
from lib.ers.adaptive_router import ToolRegistry, AdaptiveRouter

@pytest.fixture
def tool_registry() -> ToolRegistry:
    reg = ToolRegistry()
    
    async def fetch_weather(location: str) -> str:
        if location == "ErrorCity":
            raise ValueError("API Offline")
        return f"Sunny in {location}"
        
    async def fetch_weather_backup(location: str) -> str:
        return f"Backup: Sunny in {location}"

    reg.register_tool("weather", fetch_weather, "Get weather", ["weather", "api"])
    reg.register_tool("weather_backup", fetch_weather_backup, "Backup weather", ["weather", "backup"])
    
    return reg

@pytest.mark.asyncio
async def test_adaptive_router_success(tool_registry: ToolRegistry) -> None:
    router = AdaptiveRouter(tool_registry)
    step = Step(id="s1", tool="weather", outputs=["weather_result"])
    
    success, result = await router.route_step("exec1", step, {"location": "London"})
    assert success is True
    assert result == {"weather_result": "Sunny in London"}

@pytest.mark.asyncio
async def test_adaptive_router_substitute_policy(tool_registry: ToolRegistry) -> None:
    router = AdaptiveRouter(tool_registry)
    step = Step(id="s2", tool="weather", outputs=["weather_result"], on_failure="substitute")
    
    # Standard call fails, should hit substitute tool sharing 'weather' tag
    success, result = await router.route_step("exec1", step, {"location": "ErrorCity"})
    assert success is True
    assert result == {"weather_result": "Backup: Sunny in ErrorCity"}

@pytest.mark.asyncio
async def test_adaptive_router_abort_policy(tool_registry: ToolRegistry) -> None:
    router = AdaptiveRouter(tool_registry)
    step_abort = Step(id="s3", tool="weather", outputs=["weather_result"], on_failure="abort")
    
    # Should fail and abort immediately
    success, result = await router.route_step("exec1", step_abort, {"location": "ErrorCity"})
    assert success is False
    assert "error" in result
    assert "API Offline" in result["error"]
    
@pytest.mark.asyncio
async def test_adaptive_router_skip_policy(tool_registry: ToolRegistry) -> None:
    router = AdaptiveRouter(tool_registry)
    step_skip = Step(id="s4", tool="weather", on_failure="skip")
    
    # Should flag as success with a warning context since it skips over the error
    success, result = await router.route_step("exec1", step_skip, {"location": "ErrorCity"})
    assert success is True
    assert "warning" in result
