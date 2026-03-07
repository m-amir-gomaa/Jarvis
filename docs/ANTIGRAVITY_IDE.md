# Antigravity IDE Integration

Jarvis v2 provides deep integration with Neovim via an LSP bridge.

## Features
- **Smart Completions**: Asynchronous "Incomplete Results" pattern to prevent UI lag.
- **Code Actions**: "Jarvis: Fix Error" and "Jarvis: Explain Concept".
- **OOB Security**: Neovim can request capabilities which are then approved via the TUI.

## LSP Configuration
The LSP server runs on:
- **TCP Port 8002**: Standard LSP protocol.
- **HTTP Port 8001**: Security bridge and health checks.

## Neovim Commands
| Command | Action |
|---|---|
| `:JarvisIDEFix` | Fix code at cursor (requests `ide:edit`). |
| `:JarvisIDEExplain` | Explain visual selection. |
| `:JarvisIDEChat` | Open the Jarvis chat window. |

## Monitor Tab
Use `jarvis-monitor` and press `4` to see the live IDE bridge status.
