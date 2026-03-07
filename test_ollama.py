import requests
import json
url = "http://localhost:11434/api/chat"
payload = {"model": "qwen2.5-coder:7b-instruct", "messages": [{"role": "user", "content": "hello"}], "stream": True}
with requests.post(url, json=payload, stream=True) as response:
    response.raise_for_status()
    for line in response.iter_lines():
        if line:
            print(json.loads(line).get("message", {}).get("content", ""), end="")
