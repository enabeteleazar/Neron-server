#!/bin/bash
# start_neron.sh - Lance Néron v0.1 sur Homebox (Docker Compose moderne)

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
        echo -e "${RED}Docker n'est pas installé. Installez docker.io et le plugin docker compose.${NC}"
        exit 1
    fi
}

show_status() {
    echo -e "${BLUE}--- Services Néron v0.1 ---${NC}"
    docker compose ps
    echo -e "${BLUE}Core:        http://localhost:8000${NC}"
    echo -e "${BLUE}STT:         http://localhost:8001${NC}"
    echo -e "${BLUE}Memory:      http://localhost:8002${NC}"
    echo -e "${BLUE}LLM:         http://localhost:11434${NC}"
}

# --- Début du script ---
slow_echo "${BOLD}${BLUE}Vérification Docker...${NC}"
check_docker
slow_echo "${GREEN}Docker OK${NC}"

slow_echo "${BOLD}${BLUE}Construction et lancement des conteneurs Néron...${NC}"
docker compose --env-file /opt/Labo/Env/.env up --build -d 

slow_echo "${GREEN}Tous les services Néron v0.1 sont lancés !${NC}"

# --- Affichage du statut ---
show_status

slow_echo "${YELLOW}Pour suivre les logs du Core: docker compose logs -f neron-core${NC}"
