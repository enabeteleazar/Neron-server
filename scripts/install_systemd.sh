#!/usr/bin/env bash
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "This script requires sudo/root. Run: sudo ./scripts/install_systemd.sh" >&2
  exit 1
fi

echo "Installing systemd unit files..."
mkdir -p /etc/systemd/system
cp /etc/neron/deploy/neron.service /etc/systemd/system/neron.service
cp /etc/neron/deploy/neron-llm.service /etc/systemd/system/neron-llm.service

systemctl daemon-reload
systemctl enable --now neron.service
systemctl enable --now neron-llm.service

echo "Services enabled and started. Check status with: systemctl status neron.service neron-llm.service"
