/#!/bin/bash

# start_neron.sh - Lance Néron v1.13.2 sur Homebox (Docker Compose moderne)
# Inclut rebuild, relance et nettoyage Docker

set -euo pipefail

clear

# — Couleurs —
BOLD=$(tput bold)
RESET=$(tput sgr0)
RED=$(tput setaf 1)
GREEN=$(tput setaf 2)
YELLOW=$(tput setaf 3)
BLUE=$(tput setaf 4)
NC=$RESET

# — Fonctions —

slow_echo() {
    local text="$1"
    local delay="${2:-0.01}"
    for ((i=0; i<${#text}; i++)); do
        printf "%s" "${text:$i:1}"
        sleep "$delay"
    done
    echo
}

check_docker() {
    if ! command -v docker >/dev/null 2>&1; then
        echo -e "${RED}Docker n’est pas installé. Installez docker.io et le plugin docker compose.${NC}"
        exit 1
    fi
}

show_status() {
    echo
    slow_echo "${BOLD}${BLUE}Statut des conteneurs Néron:${NC}"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo
}

show_endpoints() {
    echo
    slow_echo "${BOLD}${BLUE}═══════════════════════════════════════${NC}"
    slow_echo "${BOLD}${GREEN}  Néron AI v1.13.2 — Endpoints disponibles${NC}"
    slow_echo "${BOLD}${BLUE}═══════════════════════════════════════${NC}"
    echo
    slow_echo "${YELLOW}  Interface web   : http://localhost:7860${NC}"
    slow_echo "${YELLOW}  API Core        : http://localhost:8000${NC}"
    slow_echo "${YELLOW}  Health          : http://localhost:8000/health${NC}"
    slow_echo "${YELLOW}  Métriques       : http://localhost:8000/metrics${NC}"
    echo
    slow_echo "${YELLOW}  POST /input/text   → pipeline texte${NC}"
    slow_echo "${YELLOW}  POST /input/audio  → pipeline STT → texte${NC}"
    slow_echo "${YELLOW}  POST /input/voice  → pipeline STT → LLM → TTS → audio${NC}"
    echo
    slow_echo "${YELLOW}  Logs  : docker compose logs -f neron_core${NC}"
    slow_echo "${YELLOW}  Tests : pytest modules/neron_core -v${NC}"
    slow_echo "${BOLD}${BLUE}═══════════════════════════════════════${NC}"
    echo
}

# — Début du script —

echo
slow_echo "${BOLD}${BLUE}╔════════════════════════════════════════╗${NC}"
slow_echo "${BOLD}${BLUE}║     🧠 Démarrage de Néron AI v1.13.2    ║${NC}"
slow_echo "${BOLD}${BLUE}╚════════════════════════════════════════╝${NC}"
echo

slow_echo "${BOLD}${BLUE}Vérification Docker…${NC}"
check_docker
slow_echo "${GREEN}✔ Docker OK${NC}"

# — Git update —

slow_echo "${BOLD}${BLUE}Récupération des dernières modifications…${NC}"
git fetch --all
git checkout master
git pull origin master
slow_echo "${GREEN}✔ Dépôt à jour${NC}"

# — Arrêt des conteneurs existants —

slow_echo "${BOLD}${BLUE}Arrêt des conteneurs existants…${NC}"
docker compose --env-file /opt/Neron_AI/.env down --remove-orphans
slow_echo "${GREEN}✔ Conteneurs arrêtés${NC}"

# — Construction et relance —

slow_echo "${BOLD}${BLUE}Construction et relance des services…${NC}"
docker compose --env-file /opt/Neron_AI/.env up -d --build --remove-orphans
slow_echo "${GREEN}✔ Tous les services Néron v1.13.2 sont lancés !${NC}"

# — Nettoyage Docker —

slow_echo "${BOLD}${BLUE}Nettoyage du cache Docker…${NC}"
docker system prune -af --volumes
slow_echo "${GREEN}✔ Nettoyage terminé${NC}"

# — Affichage du statut —

show_status
show_endpoints
y

