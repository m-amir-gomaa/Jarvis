# CHANGELOG v2.0.0

## [v2.0.0] - 2026-03-08

### Added
- **Speculative Execution**: Implemented sandbox pattern with auto-rollback and hallucination monitoring for safer code refactoring.
- **MCP Tool Hub**: Integrated Model Context Protocol (MCP) for dynamic tool discovery and internal memory exposure.
- **Hyper-Contextual Neovim UX**:
  - Pinned Context Buffers: Pin code snippets across files to inject into agent prompts.
  - Streaming Inline Edits: Real-time code generation within the editor.
  - Diagnostic Timeline: Visual history of diagnostic changes.
- **Privacy & Performance**:
  - Quantized FAISS/vector storage for reduced RAM usage.
  - Sub-100ms draft completions via local distilled models (FIM).
  - Confidential ERS routing to prevent data exfiltration in sensitive environments.

### Fixed
- Improved conflict resolution logic in multi-agent environments.
- Optimized RAG search latency.

### Changed
- Migrated default model routing to support Privacy levels (PRIVATE, INTERNAL, PUBLIC).
- Refactored `services/mcp_server.py` to use FastMCP.
