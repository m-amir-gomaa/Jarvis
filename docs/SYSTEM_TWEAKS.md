# Kernel & System Tweaks (non-NixOS)

While Jarvis is optimized for NixOS, it runs efficiently on any modern Linux distribution (Ubuntu, Fedora, Arch, etc.). This guide provides the manual commands and configurations required to achieve NixOS-level performance and stability on generic systems.

---

## 1. RAM Management & Swap

Jarvis (and Ollama) are RAM-intensive. To prevent the OOM (Out Of Memory) killer from terminating your session:

### ZRAM Setup (Recommended)
ZRAM creates a compressed swap area in RAM, which is significantly faster than swapping to disk.

- **Ubuntu/Debian**:
  ```bash
  sudo apt install zram-tools
  # Edit /etc/default/zramswap to set percentage (e.g., 60%)
  sudo systemctl restart zramswap
  ```
- **Fedora**:
  ```bash
  sudo dnf install zram-generator
  # Configured by default to 50% of RAM
  ```

### Swappiness
Reduce how aggressively the kernel swaps out Jarvis's memory.
```bash
# Add to /etc/sysctl.d/99-jarvis.conf
vm.swappiness = 10
vm.vfs_cache_pressure = 50
```

---

## 2. Kernel Tweaks (Performance)

### CPU Governor
Ensure your CPU stays in "performance" mode during LLM inference.
```bash
# Requires cpupower
sudo cpupower frequency-set -g performance
```

### Transparent Huge Pages (THP)
THP can improve performance for large memory allocations like model weights.
```bash
echo always | sudo tee /sys/kernel/mm/transparent_hugepage/enabled
```

### I/O Scheduler
If your Vault is on an SSD (highly recommended), ensure you are using the `mq-deadline` or `kyber` scheduler.
```bash
# Check current
cat /sys/block/sdX/queue/scheduler
# Set to mq-deadline
echo mq-deadline | sudo tee /sys/block/sdX/queue/scheduler
```

---

## 3. Persistent Systemd Services

On NixOS, these are declarative. On other distros, you must create them manually in `~/.config/systemd/user/`.

### `jarvis-coding-agent.service`
```ini
[Unit]
Description=Jarvis HTTP Sidecar for IDEs
After=network.target

[Service]
ExecStart=/usr/bin/python3 %h/NixOSenv/Jarvis/services/jarvis_lsp.py
Restart=always
Environment=PYTHONPATH=%h/NixOSenv/Jarvis
Environment=VAULT_ROOT=/THE_VAULT/jarvis

[Install]
WantedBy=default.target
```

---

## 4. Security: Ulimit & Permissions

Jarvis needs to open many file descriptors during indexing. 

### Increase File Limits
Add to `/etc/security/limits.d/jarvis.conf`:
```text
* soft nofile 65536
* hard nofile 65536
```

### Vault Permissions
Ensure the Vault directory has strict permissions:
```bash
sudo chown -R $USER:$USER /THE_VAULT/jarvis
chmod -R 700 /THE_VAULT/jarvis
```

---

## 5. Summary Table (Traditional vs. NixOS)

| Feature | NixOS Method | Traditional Linux Method |
|---------|--------------|--------------------------|
| **ZRAM** | `services.zram-generator.enable` | `zram-tools` or `zram-generator` |
| **Services** | `systemd.user.services` | Manual `.service` files in `~/.config` |
| **Sysctl** | `boot.kernel.sysctl` | Files in `/etc/sysctl.d/` |
| **Updates** | `nixos-rebuild` | `git pull` + `pip install -r requirements.txt` |

---
*Note: Always verify your specific distro's documentation before applying kernel-level changes.*
