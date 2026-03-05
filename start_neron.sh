#!/bin/bash
set -euo pipefail

BASE_DIR="/mnt/usb-storage/Neron_AI"
VENV_DIR="$BASE_DIR/venv"
LOG_DIR="$BASE_DIR/logs"
PID_FILE="/tmp/neron_system.pid"

echo "╔════════════════════════════════════════╗"
echo "║     🧠 Néron System — Démarrage         ║"
echo "╚════════════════════════════════════════╝"
echo

# Vérifications
if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ Python3 non trouvé"
    exit 1
fi

if ! command -v ollama >/dev/null 2>&1; then
    echo "❌ Ollama non trouvé"
    exit 1
fi

echo "✅ Python3 OK"
echo "✅ Ollama OK"


# Venv
if [ ! -d "$VENV_DIR" ]; then
    echo "Création du venv..."
    python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"
echo "✅ Venv activé"

# Dépendances
echo "Installation des dépendances..."
pip install --upgrade pip -q
pip install -r "$BASE_DIR/requirements.txt"
echo "✅ Dépendances installées"

# Logs
mkdir -p "$LOG_DIR"

# Déjà en cours ?
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "⚠️  Néron tourne déjà (PID $OLD_PID)"
        exit 0
    fi
fi

# Lancement
echo "Démarrage de neron_system.py..."
cd "$BASE_DIR"
python3 "$BASE_DIR/neron_system.py" &
NERON_PID=$!
echo $NERON_PID > "$PID_FILE"

echo "✅ Néron démarré (PID $NERON_PID)"
echo "Logs : tail -f $LOG_DIR/neron_system.log"

tail -f "$LOG_DIR/neron_system.log"
