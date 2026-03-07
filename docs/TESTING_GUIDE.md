# Jarvis Comprehensive Testing Guide

This guide provides a structured approach to manually testing every system, module, and capability within the Jarvis architecture. Due to the hardware constraints of CPU-only inference, some of these tests require patience (up to several minutes per response).

## 1. Core Services & Health

Before testing features, ensure the core system is healthy.

### Command:
```bash
jarvis status
```
### Expected Result:
- All daemons (`jarvis-ingest`, `jarvis-coding-agent`, etc.) show as **active**.
- The Ollama backend responds with a list of loaded models.
- The Cloud connection (if `OPENROUTER_API_KEY` is set) shows **Available**.

### Restarting & Stopping:
- **Stop everything**: `jarvis stop` (Check `jarvis status` to confirm).
- **Start everything**: `jarvis start`.

---

## 2. Model Routing & Budget Management

Jarvis dynamically chooses between local models and cloud models based on task complexity, privacy tier, and the daily token budget.

### Command:
```bash
jarvis 'plan a highly complex neural network architecture'
```
### Expected Result:
- Check `$JARVIS_ROOT/logs/jarvis.log` or run `jarvis sessions`.
- Because the task requires high reasoning (`plan`), Jarvis should route this to the cloud model (e.g., `o3-mini` or `claude-3.5-sonnet`) **only if** you haven't exhausted your `$JARVIS_ROOT/config/budget.toml` daily limit.
- If the budget is exhausted or you ask for a simple task, it routes locally to `qwen3`.

### Checking the Budget:
```bash
# Optional: Can be viewed via status or directly
cat $JARVIS_ROOT/config/budget.toml
```

---

## 3. Working Memory (Short-Term Memory)

Jarvis maintains cross-session short-term memory up to a token limit.

### Commands:
```bash
jarvis 'Hello, my favorite number is 42.'
# Wait for response...
jarvis 'What is my favorite number?'
```
### Expected Result:
- The second command should correctly identify `42` based on the context window injected from `$JARVIS_ROOT/data/sessions.db`.

### Managing Memory:
- **View active sessions**: `jarvis sessions`
- **Clear memory**: `jarvis forget` (Ask the favorite number again to confirm it forgot).

---

## 4. RAG & Semantic Memory (Long-Term Memory)

This tests the vector database (`sqlite-vec`) and the ingestion pipeline.

### Command:
```bash
# Ingest arbitrary knowledge
jarvis 'remember that the backup server IP is 192.168.1.150'
```
Wait for the ingestion pipeline to complete (you can monitor via the `jarvis dashboard`).

### Verification Command:
```bash
jarvis query 'What is the IP of the backup server?'
```
### Expected Result:
- Jarvis searches `knowledge.db`, retrieves the exact vector chunk, and answers `192.168.1.150`.

---

## 5. Assisted Language Learning (3-Layer Knowledge)

This tests the structured learning engine and syllabus generation.

### Command:
```bash
jarvis learn 'Zig'
```
### Expected Result:
- Jarvis should begin a multi-step process: generating a syllabus (Layer 1), fetching primary resources (Layer 2), and deeply analyzing concepts (Layer 3).
- **Check Progress**: Run `jarvis training` to see the competency matrix updating.
- **Check Knowledge Base**: Run `jarvis knowledge` to see the exact structured rows populated.

---

## 6. Codebase Indexing & Neovim Integration

This tests the local RAG indexing used by the background coding agent.

### Command:
```bash
cd /path/to/some/project
jarvis index .
```
### Expected Result:
- A `.jarvis_index.db` is created in that directory.

### Neovim Testing:
1. Open Neovim in that same indexed directory: `nvim src/main.rs`.
2. Check for the notification: `"Jarvis ready ✓"`.
3. Use the Neovim command `<leader>jc` (or your configured binding) to ask the agent: `"What does this file do?"`. 
4. The response should consider the local `index.db` context.

---

## 7. The TUI Dashboard Monitor

This tests the Rust-based background monitor.

### Command:
```bash
jarvis dashboard
```
### Expected Result:
- A terminal UI should pop up showing real-time logs from the Event Bus (`/tmp/jarvis_event_bus.sock`).
- Leave the dashboard open in one pane, and in another pane run `jarvis 'hello'`. You should see the LLM inference events pop into the dashboard immediately.
- Use `q` to quit.

---

## 8. Autocompletion & fzf

This tests the dynamic shell integration.

### Action:
1. Type `jarvis ` (with a space) and press `<TAB>`.
2. You should see a highly descriptive list of all 27 subcommands.
3. Type `jarvis query ` and press `<TAB>`.
4. An `fzf` window should appear offering you categories from your actual `knowledge.db`. Press enter to select one.

---

## 9. Backup & Archive Workflows

This tests the data protection pipelines.

### Commands:
```bash
# Sync vital data to the HDD
jarvis backup

# Create a zipped point-in-time snapshot
jarvis archive
```
### Expected Result:
- The `backup` command copies the Nix OS config, Neovim config, and Jarvis codebase & databases to `/THE_VAULT/JarvisData` (if mounted) or falls back to `~/Backups/Jarvis`.
- The `archive` command creates a `.tar.gz` in `~/Backups/Jarvis/archives`.

---

## Troubleshooting the Core
If any test hangs indefinitely (like a query or learning module), it is usually due to the Ollama backend running out of memory or hitting a timeout on CPU inference. 
- You can restart the engine forcefully: `systemctl restart ollama`
- You can watch the raw backend: `journalctl -u ollama -f`
