#!/bin/bash
# start_neron.sh - Néron AI v2.0 — Menu principal

set -euo pipefail
clear

# --- Couleurs ---
BOLD=$(tput bold)
RESET=$(tput sgr0)
RED=$(tput setaf 1)
GREEN=$(tput setaf 2)
YELLOW=$(tput setaf 3)
BLUE=$(tput setaf 4)
CYAN=$(tput setaf 6)
NC=$RESET

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$BASE_DIR/logs"
VENV_DIR="$BASE_DIR/venv"

slow_echo() {
    local text="$1"
    local delay="${2:-0.01}"
    for ((i=0; i<${#text}; i++)); do
        printf "%s" "${text:$i:1}"
        sleep "$delay"
    done
    echo
}

show_header() {
    clear
    echo
    slow_echo "${BOLD}${BLUE}╔════════════════════════════════════════╗${NC}"
    slow_echo "${BOLD}${BLUE}║       🧠 Néron AI v2.0 — Homebox       ║${NC}"
    slow_echo "${BOLD}${BLUE}╚════════════════════════════════════════╝${NC}"
    echo
}

show_service_status() {
    if sudo systemctl is-active --quiet neron 2>/dev/null; then
        PID=$(systemctl show -p MainPID neron | cut -d= -f2)
        MEM=$(systemctl show -p MemoryCurrent neron | cut -d= -f2)
        MEM_MB=$(( ${MEM:-0} / 1024 / 1024 ))
        echo -e "  Service : ${GREEN}${BOLD}● ACTIF${NC} (PID $PID | RAM ${MEM_MB}MB)"
    else
        echo -e "  Service : ${RED}${BOLD}● INACTIF${NC}"
    fi
    echo
}

show_menu() {
    show_header
    show_service_status
    slow_echo "${BOLD}${CYAN}  Que voulez-vous faire ?${NC}"
    echo
    echo -e "  ${BOLD}1.${NC} 🔧 Installer / Mettre à jour"
    echo -e "  ${BOLD}2.${NC} ▶  Démarrer Néron"
    echo -e "  ${BOLD}3.${NC} ⏹  Arrêter Néron"
    echo -e "  ${BOLD}4.${NC} 🔄 Redémarrer Néron"
    echo -e "  ${BOLD}5.${NC} 📄 Voir les logs"
    echo -e "  ${BOLD}6.${NC} 📊 Statut détaillé"
    echo -e "  ${BOLD}7.${NC} 🚪 Quitter"
    echo
}

do_install() {
    show_header
    slow_echo "${BOLD}${BLUE}🔧 Installation / Mise à jour…${NC}"
    echo

    # Vérif ollama
    slow_echo "${BLUE}Vérification Ollama…${NC}"
    if ! command -v ollama >/dev/null 2>&1; then
        slow_echo "${RED}❌ Ollama non trouvé — installez Ollama d'abord${NC}"
        read -rp "Appuyez sur Entrée pour continuer…"
        return
    fi
    slow_echo "${GREEN}✔ Ollama OK${NC}"

    # Dépendances système
    slow_echo "${BLUE}Installation des dépendances système…${NC}"
    sudo apt-get update -qq
    sudo apt-get install -y -qq         python3.12-venv         python3-pip         espeak         libespeak1         ffmpeg         git         curl         tree         nano
    slow_echo "${GREEN}✔ Dépendances système OK${NC}"

    # Venv
    slow_echo "${BLUE}Création/activation du venv…${NC}"
    if [ ! -d "$VENV_DIR" ]; then
        python3 -m venv "$VENV_DIR"
    fi
    source "$VENV_DIR/bin/activate"
    slow_echo "${GREEN}✔ Venv OK${NC}"

    # Dépendances
    slow_echo "${BLUE}Installation des dépendances Python…${NC}"
    pip install --upgrade pip -q
    pip install -r "$BASE_DIR/requirements.txt" -q
    slow_echo "${GREEN}✔ Dépendances OK${NC}"

    # Logs
    mkdir -p "$LOG_DIR"
    slow_echo "${GREEN}✔ Dossier logs OK${NC}"

    # Systemd
    slow_echo "${BLUE}Configuration du service systemd…${NC}"
    if [ -f "$BASE_DIR/neron.service" ]; then
        sudo cp "$BASE_DIR/neron.service" /etc/systemd/system/
        sudo systemctl daemon-reload
        sudo systemctl enable neron
        slow_echo "${GREEN}✔ Service systemd activé${NC}"
    else
        slow_echo "${YELLOW}⚠ neron.service non trouvé — skipping${NC}"
    fi

    echo
    slow_echo "${GREEN}${BOLD}✔ Installation terminée !${NC}"
    read -rp "Appuyez sur Entrée pour continuer…"
}

do_start() {
    show_header
    slow_echo "${BOLD}${BLUE}▶ Démarrage de Néron…${NC}"
    echo

    if ! command -v ollama >/dev/null 2>&1 || ! ollama list >/dev/null 2>&1; then
        slow_echo "${RED}❌ Ollama ne répond pas${NC}"
        read -rp "Appuyez sur Entrée pour continuer…"
        return
    fi

    mkdir -p "$LOG_DIR"

    if sudo systemctl is-active --quiet neron; then
        slow_echo "${YELLOW}⚠ Déjà actif — redémarrage…${NC}"
        sudo systemctl restart neron
    else
        sudo systemctl start neron
    fi

    sleep 2

    if sudo systemctl is-active --quiet neron; then
        slow_echo "${GREEN}${BOLD}✔ Néron démarré !${NC}"
        echo
        echo -e "  ${YELLOW}API  : http://localhost:8000${NC}"
        echo -e "  ${YELLOW}Docs : http://localhost:8000/docs${NC}"
    else
        slow_echo "${RED}❌ Échec du démarrage${NC}"
        sudo journalctl -u neron -n 20 --no-pager
    fi

    echo
    read -rp "Appuyez sur Entrée pour continuer…"
}

do_stop() {
    show_header
    slow_echo "${BOLD}${BLUE}⏹ Arrêt de Néron…${NC}"
    echo

    if sudo systemctl is-active --quiet neron; then
        sudo systemctl stop neron
        slow_echo "${GREEN}✔ Néron arrêté${NC}"
    else
        slow_echo "${YELLOW}⚠ Néron n'était pas actif${NC}"
    fi

    echo
    read -rp "Appuyez sur Entrée pour continuer…"
}

do_restart() {
    show_header
    slow_echo "${BOLD}${BLUE}🔄 Redémarrage de Néron…${NC}"
    echo
    sudo systemctl restart neron
    sleep 2
    if sudo systemctl is-active --quiet neron; then
        slow_echo "${GREEN}✔ Néron redémarré${NC}"
    else
        slow_echo "${RED}❌ Échec du redémarrage${NC}"
        sudo journalctl -u neron -n 20 --no-pager
    fi
    echo
    read -rp "Appuyez sur Entrée pour continuer…"
}

do_logs() {
    show_header
    slow_echo "${BOLD}${BLUE}📄 Logs en direct (Ctrl+C pour quitter)…${NC}"
    echo
    sudo journalctl -u neron -f
}

do_status() {
    show_header
    slow_echo "${BOLD}${BLUE}📊 Statut détaillé${NC}"
    echo
    sudo systemctl status neron --no-pager
    echo
    read -rp "Appuyez sur Entrée pour continuer…"
}

# --- Boucle principale ---
while true; do
    show_menu
    read -rp "  Votre choix [1-7] : " choice
    case $choice in
        1) do_install ;;
        2) do_start ;;
        3) do_stop ;;
        4) do_restart ;;
        5) do_logs ;;
        6) do_status ;;
        7)
            clear
            slow_echo "${BOLD}${BLUE}À bientôt ! 🧠${NC}"
            echo
            exit 0
            ;;
        *)
            slow_echo "${RED}Choix invalide${NC}"
            sleep 1
            ;;
    esac
done
