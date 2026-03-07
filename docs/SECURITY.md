# Jarvis v2 Security Architecture

## Trust Levels
Jarvis uses a numeric trust level system (0–4) to gate capabilities.

| Level | Name | Description |
|---|---|---|
| 0 | UNTRUSTED | Default for unknown external inputs. |
| 1 | BASIC | standard CLI/local model access. |
| 2 | ELEVATED | Access to web search, model adapters, and filesystem writes. |
| 3 | ADMIN | Access to Git writes, cloud model keys, and script execution. |
| 4 | SYSTEM | Full access (daemons, core configuration). |

## Capability Taxonomy
Capabilities are strings in the format `domain:action`. Examples:
- `ide:edit` (Level 2)
- `vcs:write` (Level 3)
- `model:external` (Level 2)

## Isolation Mechanisms
### Clone Contexts
The LSP server and ERS chains use **child contexts**. A child context:
1. Inherits its parent's trust level (or a lower ceiling).
2. Has its own private grant list.
3. Cannot escalate its own trust level.

### OOB Approvals
When a capability is requested but not yet granted, Jarvis triggers an **Out-of-Band (OOB)** approval request. This appears in the `jarvis-monitor` TUI for user review.
