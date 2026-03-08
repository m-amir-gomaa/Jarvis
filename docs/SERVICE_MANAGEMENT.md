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

## Persistent Configuration ⚙️

Jarvis allows you to tune service behavior and persistence directly from the CLI.

### Enabling/Disabling Services
By default, `jarvis start` only initializes services marked as enabled in your preferences.
- **Enable a service**: `jarvis service enable [alias]` (e.g., `jarvis service enable voice`)
- **Disable a service**: `jarvis service disable [alias]`

### Tuning Service Properties
You can override systemd properties (e.g., restart intervals, priority) and application-level thresholds persistently.

#### Systemd Overrides (Drop-ins)
These changes create a `jarvis-override.conf` in the service's systemd directory.
- `jarvis service config [alias] RestartSec 10s`
- `jarvis service config [alias] Nice 10`

#### Application Settings (JSON/TOML)
Tweak internal service logic without manual file editing.
- `jarvis service config health ram_threshold_mb 512`
- `jarvis service config health cpu_threshold_pct 85`
- `jarvis service config git check_interval_sec 7200`

> [!IMPORTANT]
> Systemd property changes (like `RestartSec`) trigger an automatic `daemon-reload`. Application settings are picked up by services dynamically on their next check cycle.

## Eco Mode & Resource Monitoring 🌱

The health monitor tracks system RAM and CPU usage. Thresholds can be customized as shown above.

- **Low RAM Alert**: Triggers when available RAM < `ram_threshold_mb`.
- **High CPU Alert**: Triggers when CPU usage > `cpu_threshold_pct`.
- **Auto-Throttling**: (Planned) Automatically pause `git` or `daily` services during critical resource contention.

## Troubleshooting

If a service refuses to start:
1. Check the logs: `journalctl --user -u jarvis-<name>.service`
2. Ensure the Jarvis virtual environment is intact.
3. Verify that all required API keys are set via `jarvis set-key`.
