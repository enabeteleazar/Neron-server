#!/bin/bash
# start_neron.sh - Lance Néron v1.4.0 sur Homebox (Docker Compose moderne)
# Inclut rebuild, relance et nettoyage Docker

set -euo pipefail

echo "╔════════════════════════════════════════╗"
echo "║  🧪 Lancement de Néron v1.4.0           "
echo "╔════════════════════════════════════════╗"
echo ""

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
    echo
    slow_echo "${BOLD}${BLUE}Statut des conteneurs Néron:${NC}"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo
}

# --- Début du script ---
slow_echo "${BOLD}${BLUE}Vérification Docker...${NC}"
check_docker
slow_echo "${GREEN}Docker OK${NC}"

# --- Passage sur master et pull ---
slow_echo "${BOLD}${BLUE}Passage sur master et récupération des dernières modifications...${NC}"
git checkout master
git pull origin master
slow_echo "${GREEN}Master à jour${NC}"

# --- Arrêt des conteneurs existants ---
slow_echo "${BOLD}${BLUE}Arrêt des conteneurs Néron existants...${NC}"
docker compose --env-file /opt/Neron_AI/.env down --remove-orphans
slow_echo "${GREEN}Conteneurs arrêtés${NC}"

# --- Reconstruction et relance ---
slow_echo "${BOLD}${BLUE}Construction et relance des conteneurs Néron...${NC}"
docker compose --env-file /opt/Neron_AI/.env up -d --build --remove-orphans
slow_echo "${GREEN}Tous les services Néron v1.4.0 sont lancés !${NC}"

# --- Nettoyage Docker ---
slow_echo "${BOLD}${BLUE}Nettoyage des conteneurs arrêtés et caches Docker...${NC}"
docker system prune -f
slow_echo "${GREEN}Nettoyage terminé${NC}"

# --- Affichage du statut ---
show_status

slow_echo "${YELLOW}Pour suivre les logs du Core: docker compose logs -f neron_core${NC}"
slow_echo "${YELLOW}Pour vérifier les metrics: curl -s http://localhost:8000/metrics | head -n 10${NC}"
