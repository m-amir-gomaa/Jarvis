import pytest
import os
import datetime
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from lib.models.secure_api_handler import SecureAPIHandler, CostTracker

@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_costs.db"
    return str(db_file)

def test_cost_tracker_persistence(temp_db):
    tracker = CostTracker(db_path=temp_db)
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Record usage
    tracker.record_usage("openai", "gpt-4", 1000, 0.03)
    tracker.record_usage("anthropic", "claude-3-opus", 500, 0.015)
    
    # Check spend
    total_spend = tracker.get_session_spend(now - datetime.timedelta(minutes=1))
    assert pytest.approx(total_spend) == 0.045

@patch("lib.models.secure_api_handler.hvac.Client")
def test_vault_integration_success(mock_hvac, temp_db):
    mock_client = MagicMock()
    mock_client.is_authenticated.return_value = True
    
    mock_read = MagicMock()
    mock_read.get.return_value.get.return_value.get.return_value = "super_secret_token"
    mock_client.secrets.kv.v2.read_secret_version = MagicMock(return_value=mock_read)
    
    mock_hvac.return_value = mock_client
    
    handler = SecureAPIHandler(vault_token="dummy", cost_tracker=CostTracker(temp_db))
    secret = handler.get_secret("anthropic", "API_KEY")
    
    assert secret == "super_secret_token"

@patch.dict(os.environ, {"EXTERNAL_API_KEY": "env_fallback_token"})
def test_vault_fallback_to_env(temp_db):
    # No vault token provided, so it skips vault
    handler = SecureAPIHandler(vault_token=None, cost_tracker=CostTracker(temp_db))
    secret = handler.get_secret("dummy/path", "EXTERNAL_API_KEY")
    assert secret == "env_fallback_token"

def test_vault_missing_secret_raises(temp_db):
    handler = SecureAPIHandler(vault_token=None, cost_tracker=CostTracker(temp_db))
    with pytest.raises(ValueError):
        handler.get_secret("dummy/path", "NON_EXISTENT_KEY")

@pytest.mark.asyncio
async def test_rate_limit_token_bucket(temp_db):
    # Setup loop time manually for precise testing
    loop = asyncio.get_event_loop()
    
    handler = SecureAPIHandler(rpm_limit=60, cost_tracker=CostTracker(temp_db))
    handler.last_refill = loop.time()
    
    # Should not block heavily
    start = loop.time()
    await handler._wait_for_rate_limit()
    end = loop.time()
    assert end - start < 0.1
    
    # Exhaust tokens
    handler.tokens = 0.0
    handler.last_refill = loop.time()
    
    # Needs to wait ~1 second for 1 token at 60 RPM
    start = loop.time()
    # Mock sleep to not actually make the test suite slow
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await handler._wait_for_rate_limit()
        mock_sleep.assert_called_once()
        args, _ = mock_sleep.call_args
        assert pytest.approx(args[0], 0.1) == 1.0


@pytest.mark.asyncio
async def test_http_429_backoff(temp_db):
    handler = SecureAPIHandler(rpm_limit=600, cost_tracker=CostTracker(temp_db))
    
    mock_session = MagicMock()
    
    # Setup response sequence: 429, then 200
    mock_resp_429 = AsyncMock()
    mock_resp_429.status = 429
    mock_resp_429.headers = {"Retry-After": "1"}
    
    mock_resp_200 = AsyncMock()
    mock_resp_200.status = 200
    mock_resp_200.raise_for_status = MagicMock() # not an async method typically
    mock_resp_200.json = AsyncMock(return_value={"usage": {"total_tokens": 1000}})
    
    # Since we are using deep mock context managers, we use a custom mocker
    class AsyncContextManagerMock:
        def __init__(self, responses):
            self.responses = responses
            self.call_count = 0
            
        async def __aenter__(self):
            resp = self.responses[self.call_count]
            self.call_count += 1
            return resp
            
        async def __aexit__(self, exc_type, exc, tb):
            pass

    mock_session.request.return_value = AsyncContextManagerMock([mock_resp_429, mock_resp_200])
    
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        res = await handler.execute_request(
            mock_session, "POST", "http://dummy", {}, {}, "provider", "model", 0.0
        )
        
        assert res == {"usage": {"total_tokens": 1000}}
        mock_sleep.assert_called_once_with(1)
        assert mock_session.request.call_count == 2 # 1 for 429, 1 for 200
