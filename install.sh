#!/bin/bash
# install.sh - Néron AI v2.0 — Bootstrap one-liner
# Usage: curl -fsSL https://raw.githubusercontent.com/enabeteleazar/Neron_AI/main/install.sh | bash
# DEV: v0803.0016

set -euo pipefail

# --- Couleurs ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

REPO_URL="https://github.com/enabeteleazar/Neron_AI.git"
INSTALL_DIR="${NERON_DIR:-/opt/neron}"
BRANCH="${NERON_BRANCH:-master}"

clear
echo -e "${BOLD}${BLUE}"
echo "╔════════════════════════════════════════╗"
echo "║     🧠 Néron AI v2.0 — Installateur    ║"
echo "╚════════════════════════════════════════╝"
echo -e "${NC}"

# --- Vérification OS ---
echo -e "${BLUE}[1/7] Vérification du système...${NC}"
if ! command -v apt-get >/dev/null 2>&1; then
    echo -e "${RED}❌ Ubuntu/Debian requis${NC}"
    exit 1
fi

# RAM
TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')
if [ "$TOTAL_RAM" -lt 2048 ]; then
    echo -e "${YELLOW}⚠ RAM détectée : ${TOTAL_RAM}MB — minimum recommandé 4GB${NC}"
    read -p "  Continuer quand même ? [o/N] " CONTINUE
    [ "$CONTINUE" = "o" ] || exit 1
else
    echo -e "${GREEN}✔ RAM : ${TOTAL_RAM}MB OK${NC}"
fi

# Disque
FREE_DISK=$(df -BG "$HOME" | awk 'NR==2{gsub("G",""); print $4}')
if [ "$FREE_DISK" -lt 10 ]; then
    echo -e "${YELLOW}⚠ Espace disque libre : ${FREE_DISK}GB — minimum recommandé 10GB${NC}"
    read -p "  Continuer quand même ? [o/N] " CONTINUE
    [ "$CONTINUE" = "o" ] || exit 1
else
    echo -e "${GREEN}✔ Disque : ${FREE_DISK}GB libre OK${NC}"
fi

# --- Dépendances de base ---
echo -e "${BLUE}[2/7] Installation des dépendances système...${NC}"
sudo apt-get update -qq

# Détecter version Python disponible
PYTHON_VENV_PKG="python3-venv"
python3 --version 2>/dev/null | grep -q "3.12" && PYTHON_VENV_PKG="python3.12-venv" || true

sudo apt-get install -y -qq \
    python3 \
    $PYTHON_VENV_PKG \
    python3-pip \
    git \
    make \
    curl \
    espeak \
    libespeak1 \
    ffmpeg \
    nano
echo -e "${GREEN}✔ Dépendances OK${NC}"

# --- Ollama ---
echo -e "${BLUE}[3/7] Vérification Ollama...${NC}"
if ! command -v ollama >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠ Ollama non trouvé — installation...${NC}"
    curl -fsSL https://ollama.ai/install.sh | sh
    echo -e "${GREEN}✔ Ollama installé${NC}"
else
    echo -e "${GREEN}✔ Ollama OK ($(ollama --version 2>/dev/null || echo 'version inconnue'))${NC}"
fi

# --- Clone / Update ---
echo -e "${BLUE}[4/7] Récupération de Néron AI...${NC}"
if [ -d "$INSTALL_DIR/.git" ]; then
    echo -e "${YELLOW}⚠ Dépôt existant — mise à jour...${NC}"
    git -C "$INSTALL_DIR" pull origin "$BRANCH"
else
    sudo mkdir -p "$(dirname $INSTALL_DIR)"
    sudo rm -rf "$INSTALL_DIR"
    echo -e "${YELLOW}  Clone: $REPO_URL → $INSTALL_DIR (branche: $BRANCH)${NC}"
    sudo git clone --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR" || {
        echo -e "${RED}❌ Erreur git clone${NC}"
        echo -e "${YELLOW}  Tentative sans sudo...${NC}"
        git clone --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR" || {
            echo -e "${RED}❌ Clone impossible${NC}"
            exit 1
        }
    }
    sudo chown -R "$(whoami):$(whoami)" "$INSTALL_DIR"
fi
# Vérifier que le clone a réussi
if [ ! -f "$INSTALL_DIR/Makefile" ]; then
    echo -e "${RED}❌ Échec du clone — Makefile introuvable${NC}"
    exit 1
fi
echo -e "${GREEN}✔ Makefile trouvé${NC}"
echo -e "${GREEN}✔ Dépôt OK${NC}"

# --- Configuration .env ---
echo -e "${BLUE}[5/7] Configuration .env...${NC}"
if [ ! -f "$INSTALL_DIR/.env" ]; then
    cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
    echo -e "${YELLOW}⚠ Fichier .env créé — pensez à le configurer${NC}"
else
    echo -e "${GREEN}✔ .env existant conservé${NC}"
fi

# --- Ollama service ---
echo -e "${BLUE}[5b/7] Service Ollama...${NC}"
if ! systemctl is-active --quiet ollama 2>/dev/null; then
    if systemctl list-unit-files | grep -q ollama; then
        sudo systemctl enable ollama
        sudo systemctl start ollama
        echo -e "${GREEN}✔ Service Ollama démarré${NC}"
    else
        echo -e "${YELLOW}⚠ Ollama sans service systemd — lancement manuel requis${NC}"
        echo -e "${YELLOW}  Exécutez : ollama serve &${NC}"
    fi
else
    echo -e "${GREEN}✔ Ollama déjà actif${NC}"
fi

# --- Make install ---
echo -e "${BLUE}[6/7] Installation via Makefile...${NC}"
make -C "$INSTALL_DIR" install

# --- Modèle Ollama ---
echo -e "${BLUE}[7/7] Modèle Ollama...${NC}"
CURRENT_MODEL=$(grep "^OLLAMA_MODEL" "$INSTALL_DIR/.env" | cut -d= -f2)
if ollama list 2>/dev/null | grep -q "$CURRENT_MODEL"; then
    echo -e "${GREEN}✔ Modèle $CURRENT_MODEL déjà présent${NC}"
else
    echo -e "${YELLOW}⚠ Modèle $CURRENT_MODEL non trouvé${NC}"
    read -p "  Télécharger maintenant ? [O/n] " DL
    [ "$DL" != "n" ] && ollama pull "$CURRENT_MODEL" && echo -e "${GREEN}✔ Modèle prêt${NC}"
fi

# --- Résumé ---
echo ""
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${GREEN}  ✅ Installation terminée !${NC}"
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  Prochaines étapes :"
echo ""
echo -e "  ${BOLD}1.${NC} Configurez vos tokens Telegram :"
echo -e "     ${YELLOW}nano $INSTALL_DIR/.env${NC}"
echo ""
echo -e "  ${BOLD}2.${NC} Variables obligatoires :"
echo -e "     ${YELLOW}TELEGRAM_BOT_TOKEN${NC}   — token @HomeBox_Neron_bot"
echo -e "     ${YELLOW}TELEGRAM_CHAT_ID${NC}     — votre chat ID"
echo -e "     ${YELLOW}WATCHDOG_BOT_TOKEN${NC}   — token @Neron_Watchdog_bot"
echo -e "     ${YELLOW}WATCHDOG_CHAT_ID${NC}     — votre chat ID"
echo ""
echo -e "  ${BOLD}3.${NC} Démarrez Néron :"
echo -e "     ${YELLOW}make -C $INSTALL_DIR start${NC}"
echo ""
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
