#!/bin/bash
# start_neron.sh - Lance Néron v2.0.0 sur Homebox (natif Ubuntu)

set -euo pipefail

clear

# --- Couleurs ---
BOLD=$(tput bold)
RESET=$(tput sgr0)
RED=$(tput setaf 1)
GREEN=$(tput setaf 2)
YELLOW=$(tput setaf 3)
BLUE=$(tput setaf 4)
NC=$RESET

BASE_DIR="/mnt/usb-storage/Neron_AI"
VENV_DIR="$BASE_DIR/venv"
LOG_DIR="$BASE_DIR/logs"
PID_FILE="/tmp/neron_core.pid"

# --- Fonctions ---

slow_echo() {
    local text="$1"
    local delay="${2:-0.01}"
    for ((i=0; i<${#text}; i++)); do
        printf "%s" "${text:$i:1}"
        sleep "$delay"
    done
    echo
}

check_deps() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo -e "${RED}❌ Python3 non trouvé${NC}"
        exit 1
    fi
    if ! command -v ollama >/dev/null 2>&1; then
        echo -e "${RED}❌ Ollama non trouvé${NC}"
        exit 1
    fi
    if ! ollama list >/dev/null 2>&1; then
        echo -e "${RED}❌ Ollama ne répond pas${NC}"
        exit 1
    fi
}

show_endpoints() {
    echo
    slow_echo "${BOLD}${BLUE}═══════════════════════════════════════${NC}"
    slow_echo "${BOLD}${GREEN}  Néron AI v2.0.0 — Endpoints disponibles${NC}"
    slow_echo "${BOLD}${BLUE}═══════════════════════════════════════${NC}"
    echo
    slow_echo "${YELLOW}  API Core        : http://localhost:8000${NC}"
    slow_echo "${YELLOW}  Health          : http://localhost:8000/health${NC}"
    echo
    slow_echo "${YELLOW}  POST /input/text   → pipeline texte${NC}"
    slow_echo "${YELLOW}  POST /input/audio  → pipeline STT → texte${NC}"
    slow_echo "${YELLOW}  POST /input/voice  → pipeline STT → LLM → TTS → audio${NC}"
    echo
    slow_echo "${YELLOW}  Logs   : tail -f $LOG_DIR/neron_core.log${NC}"
    slow_echo "${YELLOW}  Stop   : pkill -f python3 && rm -f $PID_FILE${NC}"
    slow_echo "${BOLD}${BLUE}═══════════════════════════════════════${NC}"
    echo
}

# --- Début ---

echo
slow_echo "${BOLD}${BLUE}╔════════════════════════════════════════╗${NC}"
slow_echo "${BOLD}${BLUE}║     🧠 Démarrage de Néron AI v2.0.0    ║${NC}"
slow_echo "${BOLD}${BLUE}╚════════════════════════════════════════╝${NC}"
echo

# --- Vérifications ---
slow_echo "${BOLD}${BLUE}Vérification des dépendances…${NC}"
check_deps
slow_echo "${GREEN}✔ Python3 OK${NC}"
slow_echo "${GREEN}✔ Ollama OK${NC}"

# --- Git update ---
slow_echo "${BOLD}${BLUE}Récupération des dernières modifications…${NC}"
git -C "$BASE_DIR" fetch --all
git -C "$BASE_DIR" pull origin "$(git -C "$BASE_DIR" branch --show-current)"
slow_echo "${GREEN}✔ Dépôt à jour${NC}"

# --- Arrêt instance existante ---
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        slow_echo "${BOLD}${BLUE}Arrêt de l'instance existante (PID $OLD_PID)…${NC}"
        kill "$OLD_PID"
        sleep 2
        slow_echo "${GREEN}✔ Instance arrêtée${NC}"
    fi
    rm -f "$PID_FILE"
fi

# --- Venv ---
slow_echo "${BOLD}${BLUE}Activation de l'environnement Python…${NC}"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"
slow_echo "${GREEN}✔ Venv activé${NC}"

# --- Dépendances ---
slow_echo "${BOLD}${BLUE}Installation des dépendances…${NC}"
pip install --upgrade pip -q
pip install -r "$BASE_DIR/requirements.txt" -q
slow_echo "${GREEN}✔ Dépendances installées${NC}"

# --- Logs ---
mkdir -p "$LOG_DIR"

# --- Lancement ---
slow_echo "${BOLD}${BLUE}Lancement de Néron System…${NC}"
cd "$BASE_DIR"
# Charger les variables d'environnement
set -a
source "$BASE_DIR/.env"
set +a

# Lancer neron_core (process unique)
cd "$BASE_DIR/modules/neron_core"
python3 app.py >> "$BASE_DIR/logs/neron_core.log" 2>&1 &
NERON_PID=$!
echo $NERON_PID > "$PID_FILE"
slow_echo "${GREEN}✔ Néron démarré (PID $NERON_PID)${NC}"

# --- Endpoints ---
show_endpoints

# --- Logs live ---
sleep 2
sleep 2
tail -f "$LOG_DIR/neron_core.log"
