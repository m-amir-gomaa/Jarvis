import pytest
import asyncio
from pathlib import Path
from typing import AsyncGenerator
from tempfile import TemporaryDirectory
from lib.ers.metrics_collector import MetricsCollector

@pytest.fixture
def temp_db() -> AsyncGenerator[Path, None]:
    with TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_metrics.db"
        yield db_path

@pytest.mark.asyncio
async def test_metrics_collector_lifecycle(temp_db: Path) -> None:
    collector = MetricsCollector(db_file=temp_db)
    await collector.initialize()
    
    assert temp_db.exists()
    
    await collector.log_chain_start("chain_1", "exec_1", 100.0)
    await collector.log_step("exec_1", "step_1", "tool_a", 101.0, 102.0, "success", tokens_used=50)
    await collector.log_step("exec_1", "step_2", "tool_b", 102.0, 105.0, "failure", diffs=[{"diff": "error details"}])
    await collector.log_chain_end("exec_1", 106.0, "failed", 120)
    
    report = await collector.generate_report(limit=10)
    assert len(report) == 1
    exec_report = report[0]
    
    assert exec_report["execution_id"] == "exec_1"
    assert exec_report["chain_id"] == "chain_1"
    assert exec_report["status"] == "failed"
    assert exec_report["latency"] == 6.0
    assert exec_report["total_tokens"] == 120
    
    assert len(exec_report["steps"]) == 2
    assert exec_report["steps"][0]["step_id"] == "step_1"
    assert exec_report["steps"][0]["latency"] == 1.0
    assert exec_report["steps"][1]["step_id"] == "step_2"
    assert exec_report["steps"][1]["status"] == "failure"
    
    await collector.close()

@pytest.mark.asyncio
async def test_metrics_collector_multiple_chains(temp_db: Path) -> None:
    collector = MetricsCollector(db_file=temp_db)
    await collector.initialize()
    
    for i in range(5):
        await collector.log_chain_start(f"chain_{i}", f"exec_{i}", 100.0 + i)
        await collector.log_chain_end(f"exec_{i}", 100.0 + i + 1, "success", 10)
        
    report = await collector.generate_report(limit=3)
    assert len(report) == 3
    # Ordered by ID DESC, so latest should be first
    assert report[0]["chain_id"] == "chain_4"
    assert report[2]["chain_id"] == "chain_2"
    
    await collector.close()
