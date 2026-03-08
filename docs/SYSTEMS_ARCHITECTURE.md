# Systems Architecture & IPC Documentation

This document describes the core execution engine of Jarvis v2, focusing on the deterministic interaction between management processes and the probabilistic backend kernels.

## 1. IPC & RPC Topology

Jarvis utilizes a decoupled architecture where high-level orchestration is handled by Python-based services, while heavy compute is offloaded to a **Probabilistic Inference Kernel**.

### 1.1 Service Layer (FastAPI/Uvicorn)
The system maintains dual listener interfaces on the loopback device:
- **Core Orchestration (Port 8001)**: A REST-compliant interface handled by FastAPI/Uvicorn. It manages high-level task dispatching, configuration injection, and security vault access.
- **LSP Bridge (Port 8002)**: Implements the Language Server Protocol (LSP) over JSON-RPC. This acts as the primary data conduit for IDE integrations (e.g., Neovim), enabling streaming code completions and diagnostic overlays.

### 1.2 Communication Protocols
- **Asynchronous JSON-RPC**: Used for high-throughput, low-latency signaling between the IDE and the orchestration layer.
- **SSE (Server-Sent Events) / Long Polling**: Employed by the security subsystem (`services/jarvis_lsp.py`) for Out-of-Band (OOB) capability authorization and real-time event streaming.
- **TCP Signaling**: All internal service-to-service communication is strictly local (localhost), minimizing network stack overhead and eliminating external exfiltration vectors.

### 1.3 Process Control Signaling
Process discovery is performed via process group inspection (e.g., `pgrep`). Fine-grained control of the inference backend is achieved through standard POSIX signals:
- **SIGSTOP**: Suspends the execution of the inference kernel, effectively freezing its state in VRAM without releasing allocated resources. This allows for immediate resumption while yielding CPU/GPU cycles to other system tasks.
- **SIGCONT**: Resumes a suspended kernel, restoring execution context with sub-millisecond latency.

---

## 2. Process Resource Constraints

To ensure stability on consumer-grade hardware and NixOS environments, Jarvis enforces strict resource isolation and optimization.

### 2.1 VRAM Orchestration
The primary bottleneck for local AI execution is VRAM. Jarvis manages this through a gated prefetching mechanism:
1. **Context Detection**: Neovim plugins monitor active buffer types and send prefetch requests to the Core Orchestration layer.
2. **State Freezing**: When the system detects idle periods or high-priority system tasks, it issues `SIGSTOP` to the inference kernel. This maintains the **Context Addressable Cache** in memory for rapid switch-back.

### 2.2 System Resource Limits (`ulimit`)
High-performance indexing (RAG) requires many concurrent file descriptors. The system enforces:
- `soft nofile 65536`
- `hard nofile 65536`
This prevents "Too many open files" errors during recursive repository analysis.

### 2.3 Memory Management (ZRAM & Swappiness)
On generic Linux distributions, Jarvis leverages **ZRAM** for compressed swap-in-RAM, significantly reducing IO-wait during heavy memory pressure. Kernel swappiness is tuned to `vm.swappiness = 10` to prioritize keeping the orchestration state and active caches in physical RAM.

---

## 3. Control Flow FSM: Deterministic Execution

The Jarvis **Deterministic Execution** engine (`pipelines/agent_loop.py`) operates as a state machine, decoupling the logic of reasoning from the underlying inference backend.

### 3.1 ReAct State Machine
The execution loop follows a strict state transition sequence:
1. **INPUT**: Acquisition of user intent and current environment state.
2. **REASON**: Invocation of the **Probabilistic Inference Kernel** to generate the next tactical step.
3. **ACT**: Execution of specific tools (filesystem, git, shell) based on the REASON output.
4. **OBSERVE**: Capturing the tool output and merging it into the **Context Addressable Cache**.

### 3.2 Resilience and Serialization
- **State Serialization**: Every transition is serialized to `logs/agent_<task_id>.json`. This allows for post-mortem analysis and potential recovery from runtime crashes.
- **Deterministic Retry Logic**: Failures in the ACT phase (e.g., tool errors) are treated as observations. The machine re-enters the REASON phase with the error context, allowing for self-correction.
- **Token Gating**: The `BudgetController` acts as a safety gate, inspecting usage and cost at every state transition to prevent runaway execution loops.
