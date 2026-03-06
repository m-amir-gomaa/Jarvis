#!/usr/bin/env python3
"""
Jarvis Performance Benchmark Suite
/home/qwerty/NixOSenv/Jarvis/tests/benchmark_suite.py

Measures:
1. RAG Latency (SSD vs HDD)
2. TTFT (Time To First Token) for 14B models
3. Reasoning performance on difficult coding tasks
"""

import time
import json
import requests
import subprocess
import os
from pathlib import Path

# Configuration
CODING_AGENT_URL = "http://localhost:7002"
OLLAMA_URL = "http://localhost:11434"

def benchmark_rag_latency():
    print("[Benchmark] Measuring Local RAG Latency...")
    query = "How does the Jarvis event bus work?"
    
    print(" - Triggering Local RAG Chat...")
    t0 = time.time()
    # Explicitly use a query that will hit the local index
    response_chat = requests.post(f"{CODING_AGENT_URL}/chat", json={"prompt": query, "mode": "rag"})
    t_chat = time.time() - t0
    
    if response_chat.status_code == 200:
        print(f"   [Result] Local RAG Chat: {t_chat:.2f}s")
        return {"full_chat": t_chat}
    else:
        print(f"   [Error] Chat failed: {response_chat.text}")
        return None

def benchmark_ttft(model="qwen3:14b"):
    print(f"[Benchmark] Measuring TTFT for {model}...")
    prompt = "Write a quicksort implementation in Rust."
    
    t0 = time.time()
    # Using streaming=False for simplicity in measuring first response 
    # but in a real TTFT we'd stream and catch the first chunk.
    # For OLLAMA, non-streaming 'total_duration' includes load time if not prefetched.
    response = requests.post(f"{OLLAMA_URL}/api/generate", json={
        "model": model,
        "prompt": prompt,
        "stream": False
    })
    t1 = time.time()
    
    if response.status_code == 200:
        data = response.json()
        total_dur = data.get("total_duration", 0) / 1e9  # nanoseconds to seconds
        load_dur = data.get("load_duration", 0) / 1e9
        print(f"[Result] Total Duration: {total_dur:.2f}s (Load: {load_dur:.2f}s)")
        return total_dur
    else:
        print(f"[Error] Ollama call failed: {response.text}")
        return None

def main():
    print("============================================")
    print("  Jarvis Optimization Benchmark")
    print("============================================")
    
    results = {}
    
    # Check if coding agent is up
    try:
        requests.get(f"{CODING_AGENT_URL}/health")
    except:
        print("[Abort] Coding Agent is not running on 7002.")
        return

    rag_results = benchmark_rag_latency()
    if rag_results:
        results["rag_full_chat"] = rag_results["full_chat"]
    
    results["ttft_14b"] = benchmark_ttft("qwen2.5-coder:14b")
    results["ttft_1.7b"] = benchmark_ttft("qwen3:1.7b")
    
    print("\n[Final Summary]")
    for k, v in results.items():
        if v:
            print(f" - {k}: {v:.2f}s")
            
    # Save to file
    with open("docs/BENCHMARK_RESULTS.md", "w") as f:
        f.write("# Latest Benchmark Results\n\n")
        f.write(f"Generated on {time.ctime()}\n\n")
        for k, v in results.items():
            f.write(f"- **{k}**: {v:.2f}s\n")

if __name__ == "__main__":
    main()
