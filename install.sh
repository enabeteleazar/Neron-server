#!/bin/bash
# install.sh - Néron AI v2.1 — Bootstrap one-liner
# Usage: curl -fsSL https://raw.githubusercontent.com/enabeteleazar/Neron_AI/master/install.sh | bash

set -euo pipefail

# --- Couleurs ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

REPO_URL="https://github.com/enabeteleazar/Neron_AI.git"
INSTALL_DIR="${NERON_DIR:-/etc/neron}"
BRANCH="${NERON_BRANCH:-master}"
YAML_FILE="$INSTALL_DIR/neron.yaml"

# --- Helpers yaml ---
yaml_get() {
    # yaml_get <file> <section> <key>
    python3 -c "
import yaml, sys
with open('$1') as f:
    d = yaml.safe_load(f)
try:
    print(d['$2']['$3'])
except:
    print('')
" 2>/dev/null || echo ""
}

yaml_set() {
    # yaml_set <file> <section> <key> <value>
    python3 - "$1" "$2" "$3" "$4" << 'PYEOF'
import yaml, sys
path, section, key, value = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
with open(path) as f:
    d = yaml.safe_load(f)
if section not in d:
    d[section] = {}
d[section][key] = value
with open(path, 'w') as f:
    yaml.dump(d, f, allow_unicode=True, default_flow_style=False)
PYEOF
}

# --- Configuration Telegram ---
setup_telegram() {
    echo ""
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  📱 Configuration Telegram"
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    read -p "  Voulez-vous utiliser Telegram ? [O/n] " USE_TG
    [ "$USE_TG" = "n" ] && echo -e "${YELLOW}  👉 Configurez Telegram plus tard : make telegram${NC}" && return

    echo ""
    read -p "  Avez-vous un compte Telegram ? [O/n] " HAS_TG
    if [ "$HAS_TG" = "n" ]; then
        echo -e "${YELLOW}  📲 Créez un compte sur https://telegram.org${NC}"
        echo -e "${YELLOW}  Puis relancez : make telegram${NC}"
        return
    fi

    echo ""
    read -p "  Avez-vous déjà un token de bot ? [O/n] " HAS_TOKEN
    if [ "$HAS_TOKEN" = "n" ]; then
        echo ""
        echo -e "${BOLD}  Comment créer un bot Telegram :${NC}"
        echo -e "  1. Ouvrez Telegram et cherchez ${YELLOW}@BotFather${NC}"
        echo -e "  2. Envoyez : ${YELLOW}/newbot${NC}"
        echo -e "  3. Choisissez un nom et un username (finissant par 'bot')"
        echo -e "  4. Copiez le token fourni"
        echo ""
        read -p "  Appuyez sur Entrée quand vous avez votre token..." _
    fi

    echo ""
    read -p "  Token du bot principal (conversations) : " BOT_TOKEN
    [ -z "$BOT_TOKEN" ] && echo "❌ Token vide" && return

    echo ""
    echo -e "${YELLOW}  → Envoyez un message à votre bot maintenant, puis appuyez sur Entrée${NC}"
    read -p "  Appuyez sur Entrée après avoir envoyé un message..." _

    TG_RESPONSE=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getUpdates")
    CHAT_ID=$(echo "$TG_RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
updates = data.get('result', [])
print(updates[-1]['message']['chat']['id'] if updates else '')
" 2>/dev/null || echo "")

    if [ -z "$CHAT_ID" ]; then
        echo -e "${YELLOW}  ⚠ Chat ID non récupéré automatiquement${NC}"
        read -p "  Entrez votre Chat ID manuellement : " CHAT_ID
    else
        echo -e "${GREEN}  ✔ Chat ID récupéré : $CHAT_ID${NC}"
    fi

    # Watchdog bot
    WDOG_TOKEN="$BOT_TOKEN"
    WDOG_CHAT_ID="$CHAT_ID"
    WATCHDOG_ENABLED=$(yaml_get "$YAML_FILE" "watchdog" "enabled")
    if [ "$WATCHDOG_ENABLED" = "True" ] || [ "$WATCHDOG_ENABLED" = "true" ]; then
        echo ""
        echo -e "  Créez un second bot via ${YELLOW}@BotFather${NC} pour le monitoring"
        read -p "  Token du bot monitoring : " WDOG_TOKEN
        [ -z "$WDOG_TOKEN" ] && WDOG_TOKEN="$BOT_TOKEN"
        echo -e "${YELLOW}  → Envoyez un message au bot monitoring, puis appuyez sur Entrée${NC}"
        read -p "  Appuyez sur Entrée..." _
        WDOG_CHAT_ID=$(curl -s "https://api.telegram.org/bot${WDOG_TOKEN}/getUpdates" | \
            python3 -c "
import sys, json
updates = json.load(sys.stdin).get('result', [])
print(updates[-1]['message']['chat']['id'] if updates else '')
" 2>/dev/null || echo "")
        [ -z "$WDOG_CHAT_ID" ] && read -p "  Chat ID monitoring manuellement : " WDOG_CHAT_ID
        echo -e "${GREEN}  ✔ Bot monitoring configuré${NC}"
    fi

    # Écrire dans neron.yaml
    yaml_set "$YAML_FILE" "telegram" "enabled"   "true"
    yaml_set "$YAML_FILE" "telegram" "bot_token" "$BOT_TOKEN"
    yaml_set "$YAML_FILE" "telegram" "chat_id"   "$CHAT_ID"
    yaml_set "$YAML_FILE" "watchdog" "bot_token" "$WDOG_TOKEN"
    yaml_set "$YAML_FILE" "watchdog" "chat_id"   "$WDOG_CHAT_ID"

    echo ""
    echo -e "${GREEN}  ✔ Telegram configuré dans neron.yaml${NC}"
}

# --- Mode telegram-only ---
if [ "${1:-}" = "--telegram-only" ]; then
    set +e
    INSTALL_DIR="${NERON_DIR:-/etc/neron}"
    YAML_FILE="$INSTALL_DIR/neron.yaml"
    setup_telegram
    sudo systemctl restart neron 2>/dev/null || true
    exit 0
fi

clear
echo -e "${BOLD}${BLUE}"
echo "╔════════════════════════════════════════╗"
echo "║     🧠 Néron AI v2.1 — Installateur    ║"
echo "╚════════════════════════════════════════╝"
echo -e "${NC}"

# --- Vérification OS ---
echo ""
echo -e "${BLUE}[1/7] Vérification du système...${NC}"
if ! command -v apt-get >/dev/null 2>&1; then
    echo -e "${RED}❌ Ubuntu/Debian requis${NC}"
    exit 1
fi

TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')
if [ "$TOTAL_RAM" -lt 2048 ]; then
    echo -e "${YELLOW}⚠ RAM : ${TOTAL_RAM}MB — minimum recommandé 4GB${NC}"
    read -p "  Continuer quand même ? [o/N] " CONTINUE
    [ "$CONTINUE" = "o" ] || exit 1
else
    echo -e "${GREEN}✔ RAM : ${TOTAL_RAM}MB OK${NC}"
fi

FREE_DISK=$(df -BG "$HOME" | awk 'NR==2{gsub("G",""); print $4}')
if [ "$FREE_DISK" -lt 10 ]; then
    echo -e "${YELLOW}⚠ Disque libre : ${FREE_DISK}GB — minimum recommandé 10GB${NC}"
    read -p "  Continuer quand même ? [o/N] " CONTINUE
    [ "$CONTINUE" = "o" ] || exit 1
else
    echo -e "${GREEN}✔ Disque : ${FREE_DISK}GB libre OK${NC}"
fi

# --- Dépendances ---
echo ""
echo -e "${BLUE}[2/7] Installation des dépendances système...${NC}"
sudo apt-get update -qq

PYTHON_VENV_PKG="python3-venv"
python3 --version 2>/dev/null | grep -q "3.12" && PYTHON_VENV_PKG="python3.12-venv" || true

sudo apt-get install -y -qq \
    python3 \
    $PYTHON_VENV_PKG \
    python3-pip \
    python3-yaml \
    git \
    make \
    curl \
    espeak \
    libespeak1 \
    ffmpeg \
    zstd \
    nano
echo -e "${GREEN}✔ Dépendances OK${NC}"

# --- Ollama ---
echo ""
echo -e "${BLUE}[3/7] Vérification Ollama...${NC}"
if ! command -v ollama >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠ Ollama non trouvé — installation...${NC}"
    curl -fsSL https://ollama.ai/install.sh | sh
    echo -e "${GREEN}✔ Ollama installé${NC}"
else
    echo -e "${GREEN}✔ Ollama OK ($(ollama --version 2>/dev/null || echo 'version inconnue'))${NC}"
fi

if ! systemctl is-active --quiet ollama 2>/dev/null; then
    if systemctl list-unit-files | grep -q ollama; then
        sudo systemctl enable ollama
        sudo systemctl start ollama
    else
        ollama serve &
    fi
    echo -e "${GREEN}✔ Service Ollama démarré${NC}"
else
    echo -e "${GREEN}✔ Ollama déjà actif${NC}"
fi

# --- Clone / Update ---
echo ""
echo -e "${BLUE}[4/7] Récupération de Néron AI...${NC}"
if [ -d "$INSTALL_DIR/.git" ]; then
    echo -e "${YELLOW}⚠ Dépôt existant — mise à jour...${NC}"
    git -C "$INSTALL_DIR" pull origin "$BRANCH"
else
    sudo mkdir -p "$(dirname $INSTALL_DIR)"
    sudo rm -rf "$INSTALL_DIR"
    echo -e "${YELLOW}  Clone: $REPO_URL → $INSTALL_DIR (branche: ${BRANCH})${NC}"
    sudo git clone --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR" || {
        echo -e "${YELLOW}  Tentative sans sudo...${NC}"
        git clone --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR" || {
            echo -e "${RED}❌ Clone impossible${NC}"
            exit 1
        }
    }
    sudo chown -R "$(whoami):$(whoami)" "$INSTALL_DIR"
fi

if [ ! -f "$INSTALL_DIR/Makefile" ]; then
    echo -e "${RED}❌ Échec du clone — Makefile introuvable${NC}"
    exit 1
fi
echo -e "${GREEN}✔ Dépôt OK${NC}"

# --- Configuration neron.yaml ---
echo ""
echo -e "${BLUE}[5/7] Configuration neron.yaml...${NC}"
if [ ! -f "$YAML_FILE" ]; then
    cp "$INSTALL_DIR/neron.yaml.example" "$YAML_FILE"
    echo -e "${YELLOW}⚠ neron.yaml créé depuis l'exemple — pensez à le configurer${NC}"
else
    echo -e "${GREEN}✔ neron.yaml existant conservé${NC}"
fi

# --- Make install ---
echo ""
echo -e "${BLUE}[6/7] Installation via Makefile...${NC}"
make -C "$INSTALL_DIR" install

# --- Modèle Ollama ---
echo ""
echo -e "${BLUE}[7/7] Modèle Ollama...${NC}"
CURRENT_MODEL=$(yaml_get "$YAML_FILE" "llm" "model")
CURRENT_MODEL="${CURRENT_MODEL:-llama3.2:1b}"

if ollama list 2>/dev/null | grep -q "$CURRENT_MODEL"; then
    echo -e "${GREEN}✔ Modèle $CURRENT_MODEL déjà présent${NC}"
else
    echo -e "${YELLOW}⚠ Modèle $CURRENT_MODEL non trouvé${NC}"
    read -p "  Télécharger maintenant ? [O/n] " DL
    [ "$DL" != "n" ] && ollama pull "$CURRENT_MODEL" && echo -e "${GREEN}✔ Modèle prêt${NC}"
fi

# --- Telegram ---
setup_telegram

# --- Résumé ---
echo ""
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${GREEN}  ✅ Installation terminée !${NC}"
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  Prochaines étapes :"
echo ""
echo -e "  ${BOLD}1.${NC} Vérifiez / ajustez la configuration :"
echo -e "     ${YELLOW}nano $YAML_FILE${NC}"
echo ""
echo -e "  ${BOLD}2.${NC} Démarrez Néron :"
echo -e "     ${YELLOW}make -C $INSTALL_DIR start${NC}"
echo ""
echo -e "  ${BOLD}3.${NC} Vérifiez les logs :"
echo -e "     ${YELLOW}make -C $INSTALL_DIR logs${NC}"
echo ""
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
