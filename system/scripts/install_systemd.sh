#!/usr/bin/env bash
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "This script requires sudo/root. Run: sudo ./scripts/install_systemd.sh" >&2
  exit 1
fi

BASE_DIR="/etc/neron"
SYSTEMD_DIR="$BASE_DIR/deploy"
UNITS=(
  "neron-core.service"
  "neron-core.service"
  "neron-llm.service"
  "neron-doctor.service"
  "neron-web.service"
  "neron-watchdog.service"
  "neron-llm.service"
  "neron-doctor.service"
)

echo "Installing systemd unit files..."
mkdir -p /etc/systemd/system
for unit in "${UNITS[@]}"; do
  if [ ! -f "$SYSTEMD_DIR/$unit" ]; then
    echo "Missing unit file: $SYSTEMD_DIR/$unit" >&2
    exit 1
  fi
  cp "$SYSTEMD_DIR/$unit" "/etc/systemd/system/$unit"
done

systemctl daemon-reload
for unit in "${UNITS[@]}"; do
  systemctl enable --now "$unit"
done

echo "Services enabled and started. Check status with: systemctl status ${UNITS[*]}"
