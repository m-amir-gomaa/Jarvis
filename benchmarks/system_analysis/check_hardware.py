#!/usr/bin/env python3
"""
benchmarks/system_analysis/check_hardware.py
Real hardware introspection — no simulated values.
"""
import json
import os
import platform
import subprocess
from pathlib import Path


def _read_file(path: str, default: str = "") -> str:
    try:
        return Path(path).read_text().strip()
    except Exception:
        return default


def _run(cmd: str, default: str = "") -> str:
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return default


def check_hardware() -> dict:
    result = {}

    # CPU
    cpu_info = _read_file("/proc/cpuinfo")
    model_line = next((l for l in cpu_info.splitlines() if "model name" in l), "")
    result["cpu_model"] = model_line.split(":")[-1].strip() if ":" in model_line else "unknown"
    result["cpu_cores_logical"] = os.cpu_count()
    result["cpu_freq_mhz"] = _run("grep 'cpu MHz' /proc/cpuinfo | head -1 | awk '{print $4}'", "unknown")

    # Memory
    mem_info = {}
    for line in _read_file("/proc/meminfo").splitlines():
        parts = line.split()
        if parts:
            mem_info[parts[0].rstrip(":")] = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else parts[1]
    result["ram_total_gb"] = round(mem_info.get("MemTotal", 0) / 1024 / 1024, 2)
    result["ram_available_gb"] = round(mem_info.get("MemAvailable", 0) / 1024 / 1024, 2)
    result["ram_used_gb"] = round((mem_info.get("MemTotal", 0) - mem_info.get("MemAvailable", 0)) / 1024 / 1024, 2)
    result["swap_total_gb"] = round(mem_info.get("SwapTotal", 0) / 1024 / 1024, 2)

    # ZRAM detection
    zram_devices = _run("ls /sys/block/ | grep -c zram", "0")
    result["zram_enabled"] = int(zram_devices) > 0
    if result["zram_enabled"]:
        result["zram_devices"] = int(zram_devices)

    # Disk layout
    df_out = _run("df -h --output=target,fstype,size,used,avail,pcent 2>/dev/null | tail -n +2")
    disks = []
    for line in df_out.splitlines():
        parts = line.split()
        if len(parts) >= 6:
            disks.append({"mount": parts[0], "fstype": parts[1], "size": parts[2], "used": parts[3], "avail": parts[4], "use_pct": parts[5]})
    # Show key mounts
    key_mounts = {"/", "/THE_VAULT", "/home", "/nix/store", "/tmp"}
    result["key_mounts"] = [d for d in disks if d["mount"] in key_mounts]

    # THE_VAULT specifically (jarvis data storage)
    vault_du = _run("du -sh /THE_VAULT/jarvis 2>/dev/null | cut -f1", "unknown")
    result["vault_size"] = vault_du

    # Platform
    result["os"] = platform.system()
    result["kernel"] = platform.release()
    result["is_nixos"] = Path("/etc/NIXOS").exists() or "ID=nixos" in _read_file("/etc/os-release")
    result["nixos_version"] = _read_file("/run/current-system/nixos-version", "n/a")
    result["python_version"] = platform.python_version()

    # GPU / VRAM (best-effort)
    nvcli = _run("nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader,nounits 2>/dev/null")
    if nvcli:
        parts = nvcli.split(",")
        result["gpu"] = {"name": parts[0].strip(), "vram_total_mb": parts[1].strip(), "vram_free_mb": parts[2].strip()}
    else:
        result["gpu"] = "none_detected"

    return result


if __name__ == "__main__":
    data = check_hardware()
    print(json.dumps(data, indent=2))
