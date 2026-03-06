# Jarvis Neovim Plugin

Built for speed and control, the Jarvis Neovim plugin provides a direct path to AI-driven coding without leaving your buffer.

## Architecture

- **Path**: `lua/jarvis/`
- **Main Entry**: `init.lua` (Configuration, Commands, Autocommands)
- **Agent Logic**: `agent.lua` (API Interaction, Buffer Management, UI)
- **Dependencies**: 
    - `plenary.nvim`: Used for asynchronous HTTP requests to the coding agent.
    - `nvim-notify`: Used for non-blocking UI notifications.

## User Commands

### 🌟 Productivity
- `:JarvisExplainError`: Analyzes the diagnostic (error/warning) at your cursor and displays a suggested fix as virtual text.
- `:JarvisCommit`: Generates a semantic commit message based on your staged changes. Opens in a new buffer for review.
- `:JarvisSearch <query>`: Triggers a global web research. Opens a synthesized report in a new split.

### 🛠️ Core Agent
- `:JarvisChat`: Opens a chat buffer with project context.
- `:JarvisExplain`: Explains the selected code block or current function.
- `:JarvisFix <task>`: Launches an autonomous agent to implement a feature or fix a bug in the current file.
- `:JarvisCancel`: Instantly terminates any active background task.

### ⚙️ Performance
- `:JarvisPrefetch`: Manually warm up the LLMs and load them into memory.
- `:JarvisToggleSuggestions`: Enable/disable real-time FIM (Fill-In-the-Middle) autocomplete.

## Performance Optimizations

### 1. Model Prefetching
The plugin automatically primes models to eliminate cold-start latency:
- **On Buffer Enter**: Loads the 14B `chat` model for coding tasks.
- **On Insert Mode**: Loads the 1.7B `complete` model for instant FIM suggestions.

### 2. Lock-Based Throttling
To prevent overwhelming the CPU, the plugin uses a lock mechanism in `agent.lua` to ensure multiple prefetch requests for the same model are ignored if one is already in progress.

### 3. Asynchronous Execution
All network calls use `plenary.curl`. This ensures Neovim remains 100% responsive while waiting for the LLM to generate code (which can take 10-60s on CPU).

## Key Functions (Internal)

- `M.setup(opts)`: Configures the plugin (endpoint URL, default models, enabled states).
- `M.explain_error()`: Fetches LSP diagnostics, sends to `/analyze_error`, and renders virtual text.
- `M.generate_commit()`: Calls `/summarize_git` and manages the review buffer.
- `M.search(query)`: Handles input prompts and opens research reports.
- `M.prefetch(model_alias)`: Communicates with the coding agent's warm-up endpoint.
