#!/usr/bin/env bash
# install.sh — Installation de neron-stt
set -euo pipefail

DEST="/etc/neron/stt"
SERVICE="neron-stt"

echo "━━━ neron-stt install ━━━"

# Créer le répertoire
sudo mkdir -p "$DEST"
sudo cp -r src requirements.txt "$DEST/"
sudo chown -R neron:neron "$DEST"

# Virtualenv
echo "▸ Création du virtualenv..."
sudo -u neron python3 -m venv "$DEST/venv"
sudo -u neron "$DEST/venv/bin/pip" install --upgrade pip --quiet
sudo -u neron "$DEST/venv/bin/pip" install -r "$DEST/requirements.txt" --quiet
echo "✔ Dépendances installées"

# Systemd
echo "▸ Installation du service systemd..."
sudo cp neron-stt.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE"
sudo systemctl restart "$SERVICE"

echo "✔ $SERVICE démarré"
echo "▸ Vérification : curl http://localhost:8001/health"
