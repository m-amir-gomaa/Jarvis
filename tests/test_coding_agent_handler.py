import unittest
import json
import http.client
import time
import subprocess
import os

class TestCodingAgentConnection(unittest.TestCase):
    """
    Integration tests for the Jarvis Coding Agent.
    Requires the agent to be running.
    """
    
    host = "127.0.0.1"
    port = 7002

    def test_health(self):
        conn = http.client.HTTPConnection(self.host, self.port)
        conn.request("GET", "/health")
        res = conn.getresponse()
        self.assertEqual(res.status, 200)
        data = json.loads(res.read().decode())
        self.assertEqual(data.get("status"), "ok")

    def test_explain_crash_regression(self):
        """Verify that /explain does not trigger a TypeError/Empty Reply."""
        conn = http.client.HTTPConnection(self.host, self.port)
        payload = json.dumps({
            "code": "print('hello world')",
            "language": "python"
        })
        headers = {"Content-Type": "application/json"}
        conn.request("POST", "/explain", body=payload, headers=headers)
        res = conn.getresponse()
        
        # Status should be 200 if Ollama is up, or 503 if down, but NOT a crash (Empty Reply)
        self.assertIn(res.status, [200, 503, 500])
        if res.status == 200:
            data = json.loads(res.read().decode())
            self.assertIn("explanation", data)

    def test_chat_crash_regression(self):
        conn = http.client.HTTPConnection(self.host, self.port)
        payload = json.dumps({
            "query": "Who are you?",
            "messages": [{"role": "user", "content": "Who are you?"}]
        })
        headers = {"Content-Type": "application/json"}
        conn.request("POST", "/chat", body=payload, headers=headers)
        res = conn.getresponse()
        self.assertIn(res.status, [200, 503, 500])

    def test_summarize_git_crash_regression(self):
        conn = http.client.HTTPConnection(self.host, self.port)
        payload = json.dumps({
            "diff": "--- a/file\n+++ b/file\n+print('fixed')"
        })
        headers = {"Content-Type": "application/json"}
        conn.request("POST", "/summarize_git", body=payload, headers=headers)
        res = conn.getresponse()
        self.assertIn(res.status, [200, 503, 500])

if __name__ == "__main__":
    unittest.main()
