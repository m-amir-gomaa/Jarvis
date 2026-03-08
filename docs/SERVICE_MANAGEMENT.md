# Jarvis Service Management Guide 🛠️

Jarvis relies on several background services (daemons) to provide real-time monitoring, AI assistance, and system maintenance. These are managed via `systemd --user`.

## Core Services

| Service Alias | Description | full systemd unit |
| :--- | :--- | :--- |
| `health` | Monitors system resources and service health (Watchdog). | `jarvis-health-monitor.service` |
| `git` | Summarizes git commits and tracks repository changes. | `jarvis-git-monitor.service` |
| `coding` | The AI agent responsible for collaborative coding tasks. | `jarvis-coding-agent.service` |
| `healer` | Self-healing daemon that fixes minor system inconsistencies. | `jarvis-self-healer.service` |
| `lsp` | Language Server Protocol bridge for IDE integration. | `jarvis-lsp.service` |
| `voice` | Gateway for voice commands and audio processing. | `jarvis-voice-gateway.service` |
| `daily` | Timer that triggers a daily summary of system activities. | `jarvis-daily-digest.timer` |
| `context` | Periodic update of the project context for the AI. | `jarvis-context-updater.timer` |

## CLI Management

You can now control individual services instead of the whole suite:

- **Start a service**: `jarvis start [alias]` (e.g., `jarvis start lsp`)
- **Stop a service**: `jarvis stop [alias]`
- **Restart a service**: `jarvis restart [alias]`
- **Check status**: `jarvis status [alias]`
- **Show uptime**: `jarvis uptime [alias]`

## Smart Watchdog 🛡️

The `health` service acts as a Watchdog. If it detects that a service has entered a `failed` state, it will:
1. Log the failure.
2. Attempt to restart the service automatically.
3. Send a system notification (via `notify-send`) to alert you.

> [!NOTE]
> The Watchdog will NOT attempt to restart services that were manually stopped using `jarvis stop`.

## Eco Mode & Resource Monitoring 🌱

The health monitor tracks system RAM and CPU usage every minute.

- **Low RAM Alert**: If available RAM falls below **1GB**, Jarvis sends a critical notification.
- **High CPU Alert**: If CPU usage exceeds **90%**, Jarvis warns that AI performance may be degraded.

### Future: Auto-Throttling
We are working on an "Auto-Throttle" feature that will automatically pause non-essential background tasks (like `git-monitor` or `daily-digest`) when system resources are critical.

## Troubleshooting

If a service refuses to start:
1. Check the logs: `journalctl --user -u jarvis-<name>.service`
2. Ensure the Jarvis virtual environment is intact.
3. Verify that all required API keys are set via `jarvis set-key`.
