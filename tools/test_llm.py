from lib.llm import ask, Privacy

def test_llm():
    # Should use local models
    try:
        res = ask("hi", task="chat", privacy=Privacy.PRIVATE, system="Reply with 'OK' short")
        assert res, "LLM returned empty response"
        print("Success: test_llm passed.")
    except Exception as e:
        print(f"Failed test_llm: {e}")

if __name__ == "__main__":
    test_llm()
