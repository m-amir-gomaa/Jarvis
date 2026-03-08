# 🚀 Advanced Neovim Coding with Jarvis

Jarvis V3 brings high-performance, asynchronous intelligence directly into your editor. This guide covers the advanced features enabled on the `feature/advanced-neovim` branch.

---

## 🛠️ 1. Dynamic Model Management

You can now switch the underlying models for specific tasks without restarting Neovim or the LSP server.

### Keybinding: `<leader>jm`
Or run the command: `:JarvisModel`

**Workflow**:
3.  **Instant Update**: Jarvis updates the mapping in real-time. Subsequent actions will use the new model immediately.

> [!NOTE]
> **Project Overrides**: If a `.jarvis/config.toml` exists in your project or workspace root, it can define default model aliases for that specific context, which will be automatically loaded by the Neovim agent.

---

## 🔍 2. The Diagnostic Lens (`JarvisFix`)

Instead of asking Jarvis generic questions, use your LSP diagnostics as a technical bridge.

### Workflow:
1.  Place your cursor on a line with a red error.
2.  Press `<leader>jf` (or `:JarvisFix`).
3.  **How it works**: Jarvis reads the exact LSP error message, pulls the surrounding 5 lines of context, and attempts a targeted fix using the `coder` model.

---

## 🧠 3. RAG-Augmented Code Research

You can query your entire knowledge base (books, docs, other codebases) directly from Neovim.

### Commands:
- `:JarvisChat`: Opens a prompt for a high-level question. Uses **SSE Streaming** for real-time token delivery without blocking the editor.
- `:JarvisSearch [query]`: Performs a technical search and can even open the most relevant local documentation file for you.

---

## 🛠️ 4. Extending with MCP Tools

Jarvis supports the **Model Context Protocol (MCP)**, allowing you to use specialized tools from external servers (e.g., Google Drive, SQL databases, or custom Python scripts) directly within Neovim.

### Workflow:
1.  **Configure**: Add your MCP servers to `.jarvis/mcp.toml`.
2.  **Discover**: Press `<leader>jt` to open the MCP tool picker.
3.  **Execute**: Select a tool to run it within the current Jarvis session. Jarvis handles the security handshake and result injection.

---

## 🏗️ 5. Tree-sitter Context Awareness

Jarvis is no longer "blind" to your code structure. When you run `/fix` or `/explain`, Jarvis uses Tree-sitter to:
1.  Identify the enclosing function or class.
2.  Prepend the scope definition (signature) to the prompt.
3.  Provide context-aware suggestions that understand the structural hierarchy of your code.

---

## 🐞 5. Debug Adapter Protocol (DAP) Extensions

Jarvis integrates with `nvim-dap` to provide AI-assisted debugging.

### AI Exception Analysis: `:JarvisDebugAnalyze`
When a debugger stops on an exception or at a breakpoint:
1.  Run `:JarvisDebugAnalyze`.
2.  Jarvis fetches the current stack trace from the DAP session.
3.  The agent analyzes the trace and explains the root cause in a floating window.

### Keybindings:
- `F5`: Continue
- `F10`: Step Over
- `F11`: Step Into
- `b`: Toggle Breakpoint

---

## ⚡ 4. Performance & Resource Control

Since Jarvis runs models locally on your CPU/GPU, managing system load is critical for a smooth typing experience.

### SIGSTOP / SIGCONT (Pause/Resume)
If Jarvis is performing a heavy `/fix` loop and you need to compile a large project, use the CLI in a separate terminal:
```bash
jarvis pause
```
This freezes the AI process in RAM, freeing up 100% of your CPU/GPU for the compiler. Run `jarvis resume` to finish the AI task.

### FIM (Fill-In-the-Middle) Debouncing
If ghost-text suggestions feel laggy, increase the debounce in your `setup`:
```lua
require('jarvis').setup({
  fim_debounce_ms = 1200, -- Default is 800ms
})
```

---

## 🛡️ 5. Least-Privilege Refactoring

When you run `:JarvisRefactor`, look at your **Jarvis Dashboard (`jarvis dashboard`)**.
- You will see the agent request `ide:edit` and `fs:read` capabilities.
- Jarvis defaults to **Shadow Mode** (logging only) unless you've enabled strict enforcement.
- This "Glass Box" approach ensures you always know *why* the AI is suggesting a specific code change.

---

---

## 🔍 6. Environment Observability

When troubleshooting an agent's reasoning or connection issues, you can inspect the live system logs directly from the terminal.

### CLI Command: `jarvis log show`
- **What it shows**: Structured JSON logs from the central `system.jsonl` file.
- **Filtering**: Use `--lines 50` to see a larger history.
- **Relevance**: Every MCP tool execution, ERS step, and LLM request is logged here with high fidelity.

---

## 📂 7. Project-Specific Isolation

Jarvis V3 supports hierarchical configuration, allowing you to define different behavior for different codebases.

### Workspace Configuration: `.jarvis/workspace.toml`
- **Purpose**: Define shared settings for multiple projects within a single directory tree.
- **Overrides**: Global `~/.config/jarvis/config.toml` is merged with the workspace file, with the latter taking precedence.

### Project Configuration: `.jarvis/config.toml`
- **Purpose**: Per-project fine-tuning.
- **Hierarchy**: This is the highest priority configuration file.

---

*For the full list of keybindings, see the [Interaction Interfaces](INTERFACES.md) guide.*
