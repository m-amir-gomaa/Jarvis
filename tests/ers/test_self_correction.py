import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from pathlib import Path
from tempfile import TemporaryDirectory
from lib.ers.metrics_collector import MetricsCollector
from lib.ers.self_correction import SelfCorrectionLoop, CorrectionAttempt
from typing import AsyncGenerator

@pytest.fixture
def temp_db() -> AsyncGenerator[Path, None]:
    with TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_correction_metrics.db"
        yield db_path

@pytest_asyncio.fixture
async def collector(temp_db: Path) -> AsyncGenerator[MetricsCollector, None]:
    mc = MetricsCollector(db_file=temp_db)
    await mc.initialize()
    yield mc
    await mc.close()

@pytest.mark.asyncio
async def test_self_correction_success(collector: MetricsCollector) -> None:
    loop = SelfCorrectionLoop(metrics_collector=collector, max_retries=3)
    
    # Mock LLM that fixes the error on the first try
    async def mock_llm_caller(prompt: str) -> tuple[str, dict, float]: # type: ignore
        return ("Fixed typo", {"correct_key": "val"}, 0.9)
        
    # Mock tool executor that accepts the fixed keys
    async def mock_tool_executor(tool_name: str, inputs: dict) -> tuple[bool, str]: # type: ignore
        if "correct_key" in inputs:
            return True, "Success"
        return False, "Still broken"
        
    attempt = await loop.run_correction(
        execution_id="exec_1",
        step_id="step_a",
        tool_name="dummy_tool",
        failed_inputs={"wrong_key": "val"},
        error_message="Missing correct_key",
        llm_caller=mock_llm_caller,
        tool_executor=mock_tool_executor
    )
    
    assert attempt.success is True
    assert attempt.attempt_number == 1
    assert attempt.score == 0.9
    assert attempt.corrected_inputs == {"correct_key": "val"}

@pytest.mark.asyncio
async def test_self_correction_failure_max_retries(collector: MetricsCollector) -> None:
    loop = SelfCorrectionLoop(metrics_collector=collector, max_retries=2)
    
    # Mock LLM constantly returning failing inputs
    async def mock_llm_caller(prompt: str) -> tuple[str, dict, float]: # type: ignore
        return ("Tried fix", {"bad_key": "val"}, 0.5)
        
    # Mock tool executor that always fails
    async def mock_tool_executor(tool_name: str, inputs: dict) -> tuple[bool, str]: # type: ignore
        return False, "Always breaks"
        
    attempt = await loop.run_correction(
        execution_id="exec_2",
        step_id="step_b",
        tool_name="bad_tool",
        failed_inputs={"orig_bad": "val"},
        error_message="Init fail",
        llm_caller=mock_llm_caller,
        tool_executor=mock_tool_executor
    )
    
    assert attempt.success is False
    assert attempt.attempt_number == 2  # max_retries hit
    assert "Exceeded max retries" in attempt.diagnostics
