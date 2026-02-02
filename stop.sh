#!/bin/bash
# stop_neron.sh - Arrête proprement Néron v0.2 sur Homebox

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

# --- Fonctions ---
slow_echo() {
    local text="$1"
    local delay="${2:-0.01}"
    for ((i=0; i<${#text}; i++)); do
        printf "%s" "${text:$i:1}"
        sleep $delay
    done
    echo
}

check_docker() {
    if ! command -v docker >/dev/null 2>&1; then
        echo -e "${RED}Docker n'est pas installé.${NC}"
        exit 1
    fi
}

show_running_services() {
    echo -e "${BLUE}--- Services actuellement actifs ---${NC}"
    docker compose ps --format "table {{.Service}}\t{{.Status}}" 2>/dev/null || echo "Aucun service actif"
    echo ""
}

# --- Début du script ---
echo -e "${BOLD}${RED}"
echo "╔════════════════════════════════════════╗"
echo "║   🛑 ARRÊT NÉRON v0.2 🛑              ║"
echo "╚════════════════════════════════════════╝"
echo -e "${NC}"

slow_echo "${BLUE}Vérification Docker...${NC}"
check_docker
slow_echo "${GREEN}Docker OK${NC}"
echo ""

# --- Affichage des services avant arrêt ---
show_running_services

# --- Confirmation ---
echo -e "${YELLOW}Voulez-vous arrêter tous les services Néron ? [o/N]${NC}"
read -r confirmation

if [[ ! "$confirmation" =~ ^[oO]$ ]]; then
    echo -e "${BLUE}Annulé. Aucun service n'a été arrêté.${NC}"
    exit 0
fi

# --- Arrêt des services ---
slow_echo "${BOLD}${YELLOW}Arrêt en cours des services Néron...${NC}"

docker compose --env-file /opt/Homebox_AI/.env down

echo ""
slow_echo "${GREEN}${BOLD}✅ Tous les services Néron v0.2 sont arrêtés !${NC}"
echo ""

# --- Vérification finale ---
echo -e "${BLUE}--- Vérification finale ---${NC}"
docker compose ps --format "table {{.Service}}\t{{.Status}}" 2>/dev/null || echo -e "${GREEN}✓ Aucun service actif${NC}"
echo ""

echo -e "${BLUE}Pour redémarrer Néron: ${BOLD}./start_neron.sh${NC}"
echo -e "${YELLOW}Note: Les données en mémoire sont préservées (volume persistant)${NC}"
