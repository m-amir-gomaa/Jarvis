# tests/test_llm_bridge.py
import pytest
from lib.llm import ask, Privacy

def test_ask_imports_without_error():
    assert callable(ask)
    assert Privacy.PRIVATE is not None

def test_ask_returns_string_with_mocked_ollama(monkeypatch):
    import lib.llm as llm
    llm._ollama_client = None
    
    class MockOllama:
        def chat(self, p, **kw):
            return "mocked"
            
    monkeypatch.setattr("lib.ollama_client.OllamaClient", lambda: MockOllama())
    result = ask("hello")
    assert isinstance(result, str)
    assert result == "mocked"

def test_jarvis_imports_without_modulenotfounderror():
    import importlib.util
    import sys
    # Should not raise ModuleNotFoundError
    spec = importlib.util.spec_from_file_location("jarvis", "jarvis.py")
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except SystemExit:
        pass   # jarvis.py calls sys.exit() during normal load sometimes
    except Exception as e:
        # We only care about ModuleNotFoundError here
        if isinstance(e, ModuleNotFoundError):
            pytest.fail(f"jarvis.py raised ModuleNotFoundError: {e}")
