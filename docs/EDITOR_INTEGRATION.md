# 📟 Jarvis Editor Integration & Buffer Management

This document provides a deep dive into the technical implementation of the Jarvis Neovim bridge. It covers the protocol-level communication, asynchronous buffer manipulation, and structural code awareness.

---

## 🏗️ 1. Dual-Channel Protocol Architecture

The Neovim integration operates over two distinct communication channels to balance standard compliance with specialized performance.

### A. The LSP Channel (Control Plane)
- **Service**: `jarvis-lsp` (Python/pygls)
- **Port**: `8002` (TCP)
- **Role**: Handles standard Language Server Protocol features.
  - **Diagnostics**: Errors and warnings are broadcast to Neovim. The **Heuristic Code Generation Daemon** intercepts these to provide targeted fixes.
  - **Code Actions**: Standard `quickfix` (`JarvisFix`) and `refactor` (`JarvisRefactor`) actions are exposed.
  - **Lifecycle**: Managed via `lua/jarvis/ide/lsp.lua`.

### B. The Sidecar HTTP API (Data Plane)
- **Service**: FastAPI Sidecar
- **Port**: `8001` (HTTP)
- **Role**: High-performance, low-latency endpoints for task-specific code generation.
  - **Endpoint Mapping**: Standard IDE actions are conceptually mapped to `textDocument/x-jarvis-*` requests, implemented as HTTP POSTs for simplicity and speed.
  - **Key Endpoints**:
    - `/ide/fix`: Targeted code repair using local context.
    - `/ide/complete`: FIM (Fill-In-the-Middle) ghost-text generation.
    - `/ide/refactor`: Streaming code transformations.

---

## 🧠 2. Syntax-Aware Inference Scoping

Jarvis utilizes Tree-sitter to transcend simple line-based text buffering, providing the backend with a structured "Addressable Scope."

### Addressable Scope Calculation
In `lua/jarvis/agent.lua`, the `get_treesitter_context()` function traverses the AST (Abstract Syntax Tree) upwards from the cursor:
1. **Identifier**: Locates the enclosing node (e.g., `function_definition`, `class_definition`).
2. **Exfiltration**: Extracts the signature/header of the scope.
3. **Contextual Injection**: The signature is prepended to the inference prompt.

This ensures the **Heuristic Code Generation Daemon** understands whether it is operating inside a specific method, a global class, or a module-level variable, significantly reducing hallucination.

---

## 💠 3. Buffer Meta-data (Extmarks)

For a seamless user experience, Jarvis avoids blocking the UI thread by using Neovim's **Extmarks** and **Virtual Text**.

### Asynchronous Ghost-Text (FIM)
- **Mechanism**: `nvim_buf_set_extmark`.
- **Flow**:
  1. Completion request is triggered (debounced).
  2. The daemon returns a suggestion.
  3. `lua/jarvis/ide/inline.lua` places an extmark with `virt_text_pos = "eol"`.
  4. The ghost-text is rendered in a `Comment` highlight group, mimicking a local completion.

### Inline IPC Notifications
Jarvis uses anonymous scratch buffers for ephemeral notifications.
- **Protocol**: When a long-running refactor is occurring, a placeholder buffer is often created.
- **Streaming**: Tokens are delivered via SSE (Server-Sent Events) and inserted into the buffer at the specific extmark coordinates, allowing users to witness the "Syntax-Aware Inference" in real-time.

---

## 🛠️ 4. Security & Isolation

The integration maintains a **Glass Box** security model.
1. **Token Authentication**: Shared secret in `THE_VAULT` validates the LSP handshake.
2. **Bounded Clones**: Each Neovim instance is assigned a `conn_id` and a unique `SecurityContext` clone.
3. **Audit Trail**: Every request made from the editor is audited by the `CapabilityGrantManager` on the LSP side.

---

*For usage-specific details, see the [Advanced Neovim Guide](ADVANCED_NEOVIM.md).*
