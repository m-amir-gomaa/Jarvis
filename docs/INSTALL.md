# Jarvis Installation & Deployment Guide (V3)

Jarvis is a heavy-duty AI orchestrator. This guide covers everything from standard setups to declarative NixOS deployments and advanced resource management.

## 1. Quick Start (Procedural)

For any Linux distribution, Jarvis auto-detects your platform and installs services correctly.

### Step 1: Clone & Setup
```bash
git clone https://github.com/m-amir-gomaa/Jarvis.git
cd Jarvis
make setup
```

### Step 2: Initialize the Vault
```bash
sudo mkdir -p /THE_VAULT/jarvis/{databases,logs,context,secrets,backups}
sudo chown -R $USER:users /THE_VAULT/jarvis
```

### Step 3: Install Systemd Services
This step is **platform-aware** — it detects NixOS and provides the appropriate workflow automatically:
```bash
# Install service files (traditional Linux only)
make install-services

# OR: Install AND enable auto-start on login
make install-services-enable

# Then start them:
jarvis start
```

> [!TIP]
> On **NixOS**, `make install-services` prints guidance and exits. Services are managed by `modules/jarvis.nix`. See [Section 2](#2-declarative-nixos-installation).

## 2. Declarative NixOS Installation

The recommended way to run Jarvis on NixOS is via a **Nix Module**. This ensures your services, optimizations, and binaries are always in sync.

### Create `modules/jarvis.nix`
Add this to your NixOS configuration (or import it in your `flake.nix`):

```nix
{ config, pkgs, ... }: {
  # 1. Global CLI Wrappers
  environment.systemPackages = [
    (pkgs.writeShellScriptBin "jarvis" ''
      export PYTHONPATH="/home/youruser/Jarvis"
      exec "/home/youruser/Jarvis/.venv/bin/python" "/home/youruser/Jarvis/jarvis.py" "$@"
    '')
  ];

  # 2. Kernel & RAM Tweaks
  # Prevent thrashing during heavy LLM reasoning
  boot.kernel.sysctl."vm.swappiness" = 10;
  zramSwap = {
    enable = true;
    algorithm = "zstd";
    memoryPercent = 50;
  };

  # 3. Systemd User Services (Daemons)
  systemd.user.services.jarvis-coding-agent = {
    description = "Jarvis Coding Agent Server";
    serviceConfig = {
      ExecStart = "/home/youruser/Jarvis/.venv/bin/python /home/youruser/Jarvis/services/coding_agent.py";
      Restart = "on-failure";
      Nice = 10; # Prioritize user interactivity
    };
    environment = {
      PYTHONPATH = "/home/youruser/Jarvis";
      OLLAMA_NUM_PARALLEL = "1";
    };
  };

  # 4. Scheduled Tasks (Timers)
  systemd.user.timers.jarvis-daily-digest = {
    timerConfig.OnCalendar = "*-*-* 06:00:00";
    wantedBy = [ "timers.target" ];
  };
}
```

---

## 3. AI Scheduling & Management

Jarvis manages resource-heavy LLMs by using system-level scheduling hints:

### CPU Scheduling
Inference is CPU-intensive. To prevent your IDE or TUI from lagging:
- **Nice Levels**: Use `Nice = 15` for background inference and `Nice = 10` for the coding agent.
- **Ollama Limits**: In your systemd unit for Ollama, set `CPUSchedulingPolicy = "idle"`.

### RAM Guarding
LLMs (especially 14B models) can trigger OOM (Out-of-Memory) kills.
- **MemoryMax**: Set `MemoryMax = 12G` for the Ollama service on 16GB systems.
- **ZRAM**: Always enable ZRAM on NixOS to provide a compressed buffer before hitting the physical swap file.

---

## 4. Multi-Distro Installation (Non-NixOS)

If you are on Ubuntu, Fedora, or Arch, use the **Nix Package Manager** to manage the Jarvis environment without polluting your system.

1. **Install Nix**: `curl -L https://nixos.org/nix/install | sh`
2. **Install Home-Manager**: Follow the [Home-Manager Guide](https://nix-community.github.io/home-manager/).
3. **Deploy with Flakes**: Use a simple `flake.nix` in your dotfiles to pull the dependencies.

---

## 5. Summary of Systemd Daemons

| Service                  | Role                               | Type      |
|--------------------------|------------------------------------|-----------|
| `jarvis-coding-agent`    | HTTP Sidecar for IDEs              | Simple    |
| `jarvis-health-monitor`  | Internal service watch-dog         | Simple    |
| `jarvis-daily-digest`    | Daily research summary             | Oneshot   |
| `jarvis-context-updater` | Weekly memory consolidation        | Oneshot   |

Run `jarvis start` to launch services, or `jarvis install_services` for platform-aware installation. See the **[Usage Guide](USAGE.md)** for first steps.

---
For performance optimizations on traditional (non-NixOS) Linux distributions, see the **[System Tweaks Guide](SYSTEM_TWEAKS.md)**.

---
## 6. Service Management Comparison

| Operation | NixOS | Traditional Linux |
|-----------|-------|-------------------|
| **Install services** | Edit `modules/jarvis.nix` | `make install-services` |
| **Enable auto-start** | Declared in `jarvis.nix` | `make install-services-enable` |
| **Modify unit files** | Edit `jarvis.nix` + rebuild | Drop-in files in `~/.config/systemd/user/` |
| **Apply changes** | `sudo nixos-rebuild switch` | `systemctl --user daemon-reload` |
| **Runtime control** | `jarvis start/stop/restart` | `jarvis start/stop/restart` (same!) |
