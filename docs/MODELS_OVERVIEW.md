# Jarvis Model Comparison: Local vs. Cloud

Jarvis V3 uses a hybrid intelligence model. This document provides a deep technical comparison between running models locally (via Ollama) and using external APIs (via OpenRouter or direct providers).

## 1. Technical Architecture

### Local Models (Ollama)
*   **Inference Engine**: Jarvis communicates with the local Ollama daemon over a standard REST API (`http://localhost:11434`).
*   **Quantization**: Most local models use **4-bit quantization** (e.g., `q4_K_M`) to fit 7B–14B models into consumer-grade RAM (16GB–32GB).
*   **Latency**: Bottlenecked by local CPU/GPU. On Intel i7-1165G7 (CPU-bound), expecting 1–5 tokens/sec for large models.
*   **Reliability**: 100% uptime (offline-capable).

### Cloud Models (APIs)
*   **Inference Engine**: Routed through `lib/models/adapters/` to external providers like Anthropic, OpenAI, or OpenRouter.
*   **Weights**: Generally run on full-precision (FP16/BF16) weights on high-end H100 clusters.
*   **Latency**: Network-bound + Provider load. Usually 30–100 tokens/sec.
*   **Reliability**: Dependent on internet connectivity and service availability.

## 2. System Internals & Routing

The `lib/model_router.py` acts as the traffic controller based on **Data Sensitivity** and **Security Grants**.

### The Privacy Truth Table
| Privacy Level | Data Type | Routing | Rationale |
| :--- | :--- | :--- | :--- |
| **PRIVATE** | PII, Passwords, Inbox | **Local Only** | Zero data footprint outside the machine. |
| **INTERNAL** | Codebase, Project Docs | **Local Only** | Prevents corporate IP leakage. |
| **PUBLIC** | Web Research, General Q&A | **Hybrid/Cloud** | Safe to send to vetted external providers. |

### The Budget Gate
External calls are strictly governed by `lib/budget_controller.py`:
1.  **Estimation**: Before calling the API, Jarvis estimates the request cost using token count heuristics.
2.  **Reservation**: It checks if the current `daily_limit` or `session_limit` allows the call.
3.  **Fallback**: If the budget is exceeded, Jarvis automatically downgrades the request to a local model (e.g., `qwen3:14b`).

## 3. Comparison Summary

| Feature | Local (Ollama) | Cloud (APIs) |
| :--- | :--- | :--- |
| **Cost** | $0 (Hardware only) | Per-token cost ($) |
| **Privacy** | Ultimate (Air-gapped) | Provider dependent (Encrypted) |
| **Intelligence** | High (14B-32B max) | Ultra (400B+ models) |
| **Speed** | 1-10 tok/s | 50-150 tok/s |
| **Security** | Process Isolation | Secret Key Encryption (AES-256) |

## 4. When to Use Which?

*   **Use Local if**: You are editing sensitive source code, browsing your `/THE_VAULT` data, or working without an internet connection.
*   **Use Cloud if**: You need high-level reasoning for complex architecture, broad web research synthesis, or rapid code generation for non-sensitive projects.

---
*For security implementation details, see [docs/API_KEYS.md](API_KEYS.md) and [docs/ARCHITECTURE.md](ARCHITECTURE.md).*
