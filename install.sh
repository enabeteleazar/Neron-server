#!/bin/bash
# install.sh - Néron AI v2.0 — Bootstrap one-liner
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
INSTALL_DIR="/opt/Neron_AI"

clear
echo -e "${BOLD}${BLUE}"
echo "╔════════════════════════════════════════╗"
echo "║     🧠 Néron AI v2.0 — Installateur    ║"
echo "╚════════════════════════════════════════╝"
echo -e "${NC}"

# --- Vérification OS ---
echo -e "${BLUE}[1/6] Vérification du système...${NC}"
if ! command -v apt-get >/dev/null 2>&1; then
    echo -e "${RED}❌ Ubuntu/Debian requis${NC}"
    exit 1
fi
echo -e "${GREEN}✔ OS OK${NC}"

# --- Dépendances de base ---
echo -e "${BLUE}[2/6] Installation des dépendances système...${NC}"
sudo apt-get update -qq
sudo apt-get install -y -qq \
    python3 \
    python3.12-venv \
    python3-pip \
    git \
    make \
    curl \
    espeak \
    libespeak1 \
    ffmpeg \
    nano \
    tree
echo -e "${GREEN}✔ Dépendances OK${NC}"

# --- Ollama ---
echo -e "${BLUE}[3/6] Vérification Ollama...${NC}"
if ! command -v ollama >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠ Ollama non trouvé — installation...${NC}"
    curl -fsSL https://ollama.ai/install.sh | sh
    echo -e "${GREEN}✔ Ollama installé${NC}"
else
    echo -e "${GREEN}✔ Ollama OK ($(ollama --version))${NC}"
fi

# --- Clone ---
echo -e "${BLUE}[4/6] Récupération de Néron AI...${NC}"
if [ -d "$INSTALL_DIR/.git" ]; then
    echo -e "${YELLOW}⚠ Dépôt existant — mise à jour...${NC}"
    git -C "$INSTALL_DIR" pull origin main
else
    git clone "$REPO_URL" "$INSTALL_DIR"
fi
echo -e "${GREEN}✔ Dépôt OK${NC}"

# --- Make install ---
echo -e "${BLUE}[5/6] Installation via Makefile...${NC}"
make -C "$INSTALL_DIR" install

# --- Configuration .env ---
echo -e "${BLUE}[6/6] Configuration...${NC}"
if [ ! -f "$INSTALL_DIR/.env" ]; then
    cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
    echo -e "${YELLOW}⚠ Fichier .env créé depuis .env.example${NC}"
else
    echo -e "${GREEN}✔ .env existant conservé${NC}"
fi

# --- Résumé ---
echo ""
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${GREEN}  ✅ Installation terminée !${NC}"
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  Prochaines étapes :"
echo ""
echo -e "  ${BOLD}1.${NC} Éditez votre configuration :"
echo -e "     ${YELLOW}nano $INSTALL_DIR/.env${NC}"
echo ""
echo -e "  ${BOLD}2.${NC} Variables obligatoires :"
echo -e "     ${YELLOW}TELEGRAM_BOT_TOKEN${NC}   — token @HomeBox_Neron_bot"
echo -e "     ${YELLOW}TELEGRAM_CHAT_ID${NC}     — votre chat ID"
echo -e "     ${YELLOW}WATCHDOG_BOT_TOKEN${NC}   — token @Neron_Watchdog_bot"
echo -e "     ${YELLOW}WATCHDOG_CHAT_ID${NC}     — votre chat ID"
echo -e "     ${YELLOW}OLLAMA_MODEL${NC}         — ex: llama3.2:3b"
echo ""
echo -e "  ${BOLD}3.${NC} Téléchargez un modèle :"
echo -e "     ${YELLOW}make -C $INSTALL_DIR model-set${NC}"
echo ""
echo -e "  ${BOLD}4.${NC} Démarrez Néron :"
echo -e "     ${YELLOW}make -C $INSTALL_DIR start${NC}"
echo ""
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
