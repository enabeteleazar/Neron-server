#!/bin/bash
# install.sh - Néron AI v2.0 — Installation one-liner
# Usage: curl -fsSL https://raw.githubusercontent.com/enabeteleazar/Neron_AI/main/install.sh | bash

set -euo pipefail

# --- Couleurs ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

REPO_URL="https://github.com/enabeteleazar/Neron_AI.git"
INSTALL_DIR="/mnt/usb-storage/Neron_AI"

echo -e "${BOLD}${BLUE}"
echo "╔════════════════════════════════════════╗"
echo "║     🧠 Néron AI v2.0 — Installateur    ║"
echo "╚════════════════════════════════════════╝"
echo -e "${NC}"

# --- Prérequis OS ---
echo -e "${BLUE}Vérification du système...${NC}"
if ! command -v apt-get >/dev/null 2>&1; then
    echo -e "${RED}❌ Système non supporté — Ubuntu/Debian requis${NC}"
    exit 1
fi
echo -e "${GREEN}✔ Ubuntu/Debian OK${NC}"

# --- Prérequis Python ---
if ! command -v python3 >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠ Python3 non trouvé — installation...${NC}"
    sudo apt-get install -y python3
fi
echo -e "${GREEN}✔ Python3 OK${NC}"

# --- Prérequis git ---
if ! command -v git >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠ Git non trouvé — installation...${NC}"
    sudo apt-get install -y git
fi
echo -e "${GREEN}✔ Git OK${NC}"

# --- Prérequis make ---
if ! command -v make >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠ Make non trouvé — installation...${NC}"
    sudo apt-get install -y make
fi
echo -e "${GREEN}✔ Make OK${NC}"

# --- Prérequis Ollama ---
echo -e "${BLUE}Vérification Ollama...${NC}"
if ! command -v ollama >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠ Ollama non trouvé — installation...${NC}"
    curl -fsSL https://ollama.ai/install.sh | sh
    echo -e "${GREEN}✔ Ollama installé${NC}"
else
    echo -e "${GREEN}✔ Ollama OK${NC}"
fi

# --- Clone du repo ---
echo -e "${BLUE}Clonage du dépôt Néron AI...${NC}"
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}⚠ Dossier existant — mise à jour...${NC}"
    git -C "$INSTALL_DIR" pull origin main
else
    git clone "$REPO_URL" "$INSTALL_DIR"
fi
echo -e "${GREEN}✔ Dépôt OK${NC}"

# --- Installation via Makefile ---
echo -e "${BLUE}Installation des dépendances...${NC}"
make -C "$INSTALL_DIR" install

# --- Configuration .env ---
echo ""
echo -e "${BOLD}${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${YELLOW}  ⚙️  Configuration requise${NC}"
echo -e "${BOLD}${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  Éditez votre fichier .env :"
echo -e "  ${BOLD}nano $INSTALL_DIR/.env${NC}"
echo ""
echo -e "  Variables obligatoires :"
echo -e "  ${YELLOW}TELEGRAM_BOT_TOKEN${NC}   — token @HomeBox_Neron_bot"
echo -e "  ${YELLOW}TELEGRAM_CHAT_ID${NC}     — votre chat ID"
echo -e "  ${YELLOW}WATCHDOG_BOT_TOKEN${NC}   — token @Neron_Watchdog_bot"
echo -e "  ${YELLOW}WATCHDOG_CHAT_ID${NC}     — votre chat ID"
echo -e "  ${YELLOW}OLLAMA_MODEL${NC}         — ex: llama3.2:3b"
echo ""
echo -e "${BOLD}${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BOLD}${GREEN}✅ Installation terminée !${NC}"
echo ""
echo -e "  Prochaines étapes :"
echo -e "  ${BOLD}1.${NC} nano $INSTALL_DIR/.env"
echo -e "  ${BOLD}2.${NC} ollama pull llama3.2:3b"
echo -e "  ${BOLD}3.${NC} make -C $INSTALL_DIR start"
echo ""
