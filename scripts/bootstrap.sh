#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/etc/neron"

echo "Installing system build deps (requires sudo)..."
sudo apt-get update && sudo apt-get install -y build-essential libyaml-dev python3-dev

python -m venv .venv
. .venv/bin/activate
pip install --upgrade pip

# Install test deps using constraints file (absolute path)
pip install -r server/requirements-test.txt --constraint "$BASE_DIR/constraints.txt" --prefer-binary

echo "Bootstrap complete"
