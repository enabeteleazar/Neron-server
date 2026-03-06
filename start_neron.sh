#!/bin/bash
# start_neron.sh - Néron AI v2.0 — via systemd

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
LOG_DIR="$BASE_DIR/logs"

slow_echo() {
    local text="$1"
    local delay="${2:-0.01}"
    for ((i=0; i<${#text}; i++)); do
        printf "%s" "${text:$i:1}"
        sleep "$delay"
    done
    echo
}

show_status() {
    echo
    slow_echo "${BOLD}${BLUE}═══════════════════════════════════════${NC}"
    slow_echo "${BOLD}${GREEN}  Néron AI v2.0 — Endpoints${NC}"
    slow_echo "${BOLD}${BLUE}═══════════════════════════════════════${NC}"
    echo
    slow_echo "${YELLOW}  API Core   : http://localhost:8000${NC}"
    slow_echo "${YELLOW}  Health     : http://localhost:8000/health${NC}"
    echo
    slow_echo "${YELLOW}  Logs       : sudo journalctl -u neron -f${NC}"
    slow_echo "${YELLOW}  Stop       : sudo systemctl stop neron${NC}"
    slow_echo "${YELLOW}  Restart    : sudo systemctl restart neron${NC}"
    slow_echo "${YELLOW}  Status     : sudo systemctl status neron${NC}"
    slow_echo "${BOLD}${BLUE}═══════════════════════════════════════${NC}"
    echo
}

# --- Header ---
echo
slow_echo "${BOLD}${BLUE}╔════════════════════════════════════════╗${NC}"
slow_echo "${BOLD}${BLUE}║     🧠 Néron AI v2.0 — systemd         ║${NC}"
slow_echo "${BOLD}${BLUE}╚════════════════════════════════════════╝${NC}"
echo

# --- Vérifications ---
slow_echo "${BOLD}${BLUE}Vérification Ollama…${NC}"
if ! command -v ollama >/dev/null 2>&1; then
    slow_echo "${RED}❌ Ollama non trouvé${NC}"
    exit 1
fi
if ! ollama list >/dev/null 2>&1; then
    slow_echo "${RED}❌ Ollama ne répond pas${NC}"
    exit 1
fi
slow_echo "${GREEN}✔ Ollama OK${NC}"

# --- Logs ---
mkdir -p "$LOG_DIR"

# --- Démarrage via systemd ---
slow_echo "${BOLD}${BLUE}Démarrage du service Néron…${NC}"

# Si déjà actif → restart
if sudo systemctl is-active --quiet neron; then
    slow_echo "${YELLOW}⚠ Service déjà actif — redémarrage…${NC}"
    sudo systemctl restart neron
else
    sudo systemctl start neron
fi

sleep 2

# Vérifier que le service tourne
if sudo systemctl is-active --quiet neron; then
    slow_echo "${GREEN}✔ Néron démarré (systemd)${NC}"
else
    slow_echo "${RED}❌ Échec du démarrage — vérifier les logs${NC}"
    sudo journalctl -u neron -n 20 --no-pager
    exit 1
fi

# --- Status et endpoints ---
show_status

# --- Logs live ---
slow_echo "${YELLOW}Logs en direct (Ctrl+C pour quitter) :${NC}"
sleep 1
sudo journalctl -u neron -f
