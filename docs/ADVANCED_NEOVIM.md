# 🚀 Advanced Neovim Coding with Jarvis

This guide explains how to leverage Jarvis V3 to its maximum potential within the Neovim environment.

---

## 🛠️ 1. Dynamic Model Management

You can now switch the underlying models for specific tasks without restarting Neovim or the LSP server.

### Keybinding: `<leader>jm`
Or run the command: `:JarvisModel`

**Workflow**:
1.  **Select Alias**: Choose which "role" you want to update (e.g., `coder` for refactors, `chat` for queries, `reason` for deep analysis).
2.  **Select Model**: Choose from discovered local models (via Ollama) or cloud providers.
3.  **Instant Update**: Jarvis updates the mapping in real-time. Subsequent actions will use the new model immediately.

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
- `:JarvisChat`: Opens a prompt for a high-level question. Jarvis will search your semantic memory before answering.
- `:JarvisSearch [query]`: Performs a technical search and can even open the most relevant local documentation file for you.

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

*For the full list of keybindings, see the [Interaction Interfaces](INTERFACES.md) guide.*
