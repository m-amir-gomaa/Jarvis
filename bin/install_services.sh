#!/usr/bin/env bash
# =============================================================================
# Jarvis Service Installer — NixOS & Traditional Linux
# =============================================================================
# Usage:
#   bash bin/install_services.sh            # Install all core services
#   bash bin/install_services.sh --enable   # Install + enable (auto-start on login)
#   bash bin/install_services.sh --uninstall
#
# On NixOS: This script will print guidance. Services are managed by jarvis.nix.
# On Linux: This script installs .service and .timer files into
#            ~/.config/systemd/user/ and reloads the daemon.
# =============================================================================

set -euo pipefail

JARVIS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VAULT_ROOT="${VAULT_ROOT:-/THE_VAULT/jarvis}"
VENV_PY="${JARVIS_ROOT}/.venv/bin/python"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"
UID_VAL="$(id -u)"
TEMPLATES_DIR="${JARVIS_ROOT}/services/templates"

ENABLE_ON_INSTALL=false
UNINSTALL=false

for arg in "$@"; do
  case "$arg" in
    --enable) ENABLE_ON_INSTALL=true ;;
    --uninstall) UNINSTALL=true ;;
  esac
done

# --- OS Detection ---
detect_nixos() {
  if [[ -f /etc/os-release ]]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    [[ "${ID:-}" == "nixos" ]] && return 0
  fi
  # Also detect if the Nix store is in use even on NixOS with custom configs
  [[ -d /nix/store ]] && [[ -f /etc/NIXOS ]] && return 0
  return 1
}

# --- Core Services & Timers ---
SERVICES=(
  "jarvis-health-monitor"
  "jarvis-git-monitor"
  "jarvis-coding-agent"
  "jarvis-self-healer"
  "jarvis-lsp"
  "jarvis-voice-gateway"
  "jarvis-daily-digest"
  "jarvis-context-updater"
)

TIMERS=(
  "jarvis-daily-digest"
  "jarvis-context-updater"
)

# ── NixOS: Guidance Only ──────────────────────────────────────────────────────
if detect_nixos; then
  echo ""
  echo "╔══════════════════════════════════════════════════════════════╗"
  echo "║           NixOS Detected — Services Managed by Nix          ║"
  echo "╚══════════════════════════════════════════════════════════════╝"
  echo ""
  echo "On NixOS, Jarvis services are declared in:"
  echo "  ~/NixOSenv/modules/jarvis.nix"
  echo ""
  echo "To enable or change services, edit jarvis.nix and apply with:"
  echo "  sudo nixos-rebuild switch --flake ~/NixOSenv#nixos"
  echo ""
  echo "Current managed services (from jarvis.nix):"
  for svc in "${SERVICES[@]}"; do
    status=$(systemctl --user is-active "${svc}" 2>/dev/null || echo "inactive")
    echo "  ${svc}: ${status}"
  done
  echo ""
  echo "You can still use 'jarvis start/stop/restart <alias>' to manage"
  echo "running service instances without modifying the Nix configuration."
  echo ""
  echo "To add or remove services from the NixOS configuration, edit:"
  echo "  systemd.user.services in ~/NixOSenv/modules/jarvis.nix"
  exit 0
fi

# ── Traditional Linux: Install ────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║        Traditional Linux — Installing Jarvis Services       ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check venv exists
if [[ ! -f "${VENV_PY}" ]]; then
  echo "Error: Python venv not found at ${VENV_PY}"
  echo "       Please run 'make setup' first."
  exit 1
fi

# Check VAULT_ROOT
if [[ ! -d "${VAULT_ROOT}" ]]; then
  echo "Warning: VAULT_ROOT (${VAULT_ROOT}) does not exist."
  echo "         Creating it now..."
  mkdir -p "${VAULT_ROOT}"/{databases,logs,context,secrets,backups}
fi

# Check template directory
if [[ ! -d "${TEMPLATES_DIR}" ]]; then
  echo "Error: Template directory not found at ${TEMPLATES_DIR}"
  exit 1
fi

# Uninstall mode
if [[ "${UNINSTALL}" == true ]]; then
  echo "Uninstalling Jarvis services..."
  for svc in "${SERVICES[@]}"; do
    systemctl --user stop "${svc}" 2>/dev/null || true
    systemctl --user disable "${svc}" 2>/dev/null || true
    rm -f "${SYSTEMD_USER_DIR}/${svc}.service"
  done
  for tmr in "${TIMERS[@]}"; do
    systemctl --user stop "${tmr}.timer" 2>/dev/null || true
    systemctl --user disable "${tmr}.timer" 2>/dev/null || true
    rm -f "${SYSTEMD_USER_DIR}/${tmr}.timer"
  done
  systemctl --user daemon-reload
  echo "Jarvis services uninstalled."
  exit 0
fi

mkdir -p "${SYSTEMD_USER_DIR}"

# Install helper: substitute template placeholders and write to systemd dir
install_unit() {
  local template_name="$1"
  local template_path="${TEMPLATES_DIR}/${template_name}"
  local dest="${SYSTEMD_USER_DIR}/${template_name}"

  if [[ ! -f "${template_path}" ]]; then
    echo "  ⚠ Template not found: ${template_path} (skipping)"
    return
  fi

  sed \
    -e "s|__JARVIS_ROOT__|${JARVIS_ROOT}|g" \
    -e "s|__VAULT_ROOT__|${VAULT_ROOT}|g" \
    -e "s|__VENV_PY__|${VENV_PY}|g" \
    -e "s|__UID__|${UID_VAL}|g" \
    "${template_path}" > "${dest}"

  chmod 644 "${dest}"
  echo "  ✓ Installed: ${dest}"
}

echo "Installing service units from templates..."
for svc in "${SERVICES[@]}"; do
  install_unit "${svc}.service"
done

echo "Installing timer units from templates..."
for tmr in "${TIMERS[@]}"; do
  install_unit "${tmr}.timer"
done

# Reload the systemd user daemon
echo ""
echo "Reloading systemd daemon..."
systemctl --user daemon-reload

# Optionally enable services for auto-start on login
if [[ "${ENABLE_ON_INSTALL}" == true ]]; then
  echo ""
  echo "Enabling core services (health-monitor, git-monitor)..."
  systemctl --user enable jarvis-health-monitor.service jarvis-git-monitor.service
  systemctl --user enable --now jarvis-daily-digest.timer jarvis-context-updater.timer
  echo "  ✓ Services enabled. Run 'jarvis start' to start them now."
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                   Installation Complete                     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "  jarvis start           # Start all enabled services"
echo "  jarvis status          # Check service health"
echo ""
echo "To enable auto-start on login, re-run with:"
echo "  bash bin/install_services.sh --enable"
