# 🚀 Advanced Usage: Concurrency & Monitoring

This guide is for power users who want to push Jarvis to its functional limits, managing complex AI workloads and local system resources with precision.

---

## ⚡ 1. Orchestrate Parallel AI Thoughts (ERS Concurrency)

Jarvis's **ERS (External Reasoning System)** isn't just a sequential script; it's an asynchronous execution engine. You can execute multiple AI thoughts in parallel to drastically reduce latency in complex chains.

### Using `batch_group`
In your `.yaml` chain definitions, you can group steps together. Any steps sharing the same `batch_group` name will execute concurrently.

```yaml
# Example: Parallel Research & Code Analysis
steps:
  - id: parallel_intel_1
    batch_group: "intel_gathering"
    prompt_template: "Search the web for the latest [X] documentation."
  - id: parallel_intel_2
    batch_group: "intel_gathering"
    prompt_template: "Analyze the local file [Y] for architecture patterns."
```

### The RAM Gate Guard
To prevent your system from swapping during heavy local inference, Jarvis implements a **RAM Gate**.
- **Threshold**: `1024 MB` available RAM.
- **Behavior**: If your system has less than 1GB of free RAM, Jarvis will automatically **serialize** batch steps (running them one by one) to protect system stability.

---

## 🔍 2. Skillful "Glass Box" Monitoring

Jarvis isn't a "magic box"; it's a **Glass Box**. Advanced monitoring allows you to debug reasoning failures in real-time.

### Real-Time Chain Inspection
Launch the dashboard and switch to the **ERS Tab (Key: 3)**.
- **Progress Bars**: Monitor the exact step execution status.
- **Context Injection**: Use this to see exactly what data from `Step 1` was "augmented" into the prompt for `Step 2`.

### Security Audit Tailing
If a chain seems "stuck," it's often waiting for a capability grant. Switch to the **Security Tab (Key: 2)**.
- **OOB Requests**: You will see the exact capability (`fs:read`, `net:search`) that the agent is requesting.
- **Resolution**: Instead of waiting, you can preemptively run `jarvis approve <ID>` from another terminal.

---

## 🛠️ 3. Managing Multiple Concurrent Sessions

You can run multiple Jarvis queries or chains simultaneously.

### Isolation through Context
Each command triggers a unique `SecurityContext`.
- **Session Tokens**: All sessions share the same primary identity but have isolated `agent_id` prefixes (e.g., `ers:step_1`, `nvim:buffer_42`).
- **Resource Contention**: Jarvis uses a FIFO approach for the Ollama model load. If multiple sessions request different models, the **Model Router** will handle the queue.

### Performance Tip: SIGSTOP/SIGCONT
If you need to reclaim your CPU/GPU for a heavy compilation while Jarvis is thinking, use:
```bash
jarvis pause
```
This sends `SIGSTOP` to the Ollama process, freezing the AI session in RAM without losing state. Run `jarvis resume` when you're ready to continue.

---

## 💾 4. SQL Performance Tuning for RAG

For very large knowledge bases, you can optimize your manual queries using internal flags:

`jarvis query "Question" --category "specific_doc" --layer 2`

By specifying the `layer` (Docs vs Theory), you narrow the vector search space, significantly reducing KNN search time on CPU-bound hardware like the i7-1165G7.

---

*For technical architecture details, see the [Deep Dive](DEEP_DIVE.md).*
