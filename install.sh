#!/bin/bash
# install.sh - Néron AI v2.1 — Bootstrap one-liner
# Usage: curl -fsSL https://raw.githubusercontent.com/enabeteleazar/Neron_AI/master/install.sh | bash

set -euo pipefail
clear

# --- Couleurs terminal ---
BOLD=$(tput bold)
RESET=$(tput sgr0)
RED=$(tput setaf 1)
GREEN=$(tput setaf 2)
YELLOW=$(tput setaf 3)
BLUE=$(tput setaf 4)
CYAN=$(tput setaf 6)
NC=$RESET

# --- Affichage lent ---
slow_echo() {
    local text="$1"
    local delay="${2:-0.02}"
    for ((i=0; i<${#text}; i++)); do
        printf "%s" "${text:$i:1}"
        sleep $delay
    done
    echo
}

# --- Spinner ---
spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='|/-\'
    while ps -p "$pid" > /dev/null 2>&1; do
        local temp=${spinstr#?}
        printf " ${BLUE}[%c]${NC}  " "${spinstr}"
        spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "      \b\b\b\b\b\b"
}

# --- Helpers affichage ---
ok()   { echo -e "  ${GREEN}${BOLD}✔${NC} $1"; }
fail() { echo -e "  ${RED}${BOLD}✘${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC}  $1"; }
step() { echo -e "\n${BLUE}${BOLD}[$1]${NC} $2"; }

REPO_URL="https://github.com/enabeteleazar/Neron_AI.git"
INSTALL_DIR="${NERON_DIR:-/etc/neron}"
BRANCH="${NERON_BRANCH:-master}"
YAML_FILE="$INSTALL_DIR/neron.yaml"

# --- Helpers yaml ---
yaml_get() {
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
    echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    slow_echo "  📱 Configuration Telegram" 0.03
    echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    read -p "  Voulez-vous utiliser Telegram ? [O/n] " USE_TG
    [ "$USE_TG" = "n" ] && warn "Configurez Telegram plus tard : make telegram" && return

    echo ""
    read -p "  Avez-vous un compte Telegram ? [O/n] " HAS_TG
    if [ "$HAS_TG" = "n" ]; then
        warn "Créez un compte sur https://telegram.org"
        warn "Puis relancez : make telegram"
        return
    fi

    echo ""
    read -p "  Avez-vous déjà un token de bot ? [O/n] " HAS_TOKEN
    if [ "$HAS_TOKEN" = "n" ]; then
        echo ""
        echo -e "  ${BOLD}Comment créer un bot Telegram :${NC}"
        echo -e "  1. Cherchez ${YELLOW}@BotFather${NC} sur Telegram"
        echo -e "  2. Envoyez : ${YELLOW}/newbot${NC}"
        echo -e "  3. Choisissez un nom et un username (finissant par 'bot')"
        echo -e "  4. Copiez le token fourni"
        echo ""
        read -p "  Appuyez sur Entrée quand vous avez votre token..." _
    fi

    echo ""
    read -p "  Token du bot principal (conversations) : " BOT_TOKEN
    [ -z "$BOT_TOKEN" ] && fail "Token vide" && return

    echo ""
    warn "Envoyez un message à votre bot, puis appuyez sur Entrée"
    read -p "  Appuyez sur Entrée après avoir envoyé un message..." _

    TG_RESPONSE=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getUpdates")
    CHAT_ID=$(echo "$TG_RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
updates = data.get('result', [])
print(updates[-1]['message']['chat']['id'] if updates else '')
" 2>/dev/null || echo "")

    if [ -z "$CHAT_ID" ]; then
        warn "Chat ID non récupéré automatiquement"
        read -p "  Entrez votre Chat ID manuellement : " CHAT_ID
    else
        ok "Chat ID récupéré : $CHAT_ID"
    fi

    WDOG_TOKEN="$BOT_TOKEN"
    WDOG_CHAT_ID="$CHAT_ID"
    WATCHDOG_ENABLED=$(yaml_get "$YAML_FILE" "watchdog" "enabled")
    if [ "$WATCHDOG_ENABLED" = "True" ] || [ "$WATCHDOG_ENABLED" = "true" ]; then
        echo ""
        echo -e "  Créez un second bot via ${YELLOW}@BotFather${NC} pour le monitoring"
        read -p "  Token du bot monitoring : " WDOG_TOKEN
        [ -z "$WDOG_TOKEN" ] && WDOG_TOKEN="$BOT_TOKEN"
        warn "Envoyez un message au bot monitoring, puis appuyez sur Entrée"
        read -p "  Appuyez sur Entrée..." _
        WDOG_CHAT_ID=$(curl -s "https://api.telegram.org/bot${WDOG_TOKEN}/getUpdates" | \
            python3 -c "
import sys, json
updates = json.load(sys.stdin).get('result', [])
print(updates[-1]['message']['chat']['id'] if updates else '')
" 2>/dev/null || echo "")
        [ -z "$WDOG_CHAT_ID" ] && read -p "  Chat ID monitoring manuellement : " WDOG_CHAT_ID
        ok "Bot monitoring configuré"
    fi

    yaml_set "$YAML_FILE" "telegram" "enabled"   "true"
    yaml_set "$YAML_FILE" "telegram" "bot_token" "$BOT_TOKEN"
    yaml_set "$YAML_FILE" "telegram" "chat_id"   "$CHAT_ID"
    yaml_set "$YAML_FILE" "watchdog" "bot_token" "$WDOG_TOKEN"
    yaml_set "$YAML_FILE" "watchdog" "chat_id"   "$WDOG_CHAT_ID"

    echo ""
    ok "Telegram configuré dans neron.yaml"
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

# --- Bannière ---
echo ""
echo -e "${BOLD}${BLUE}"
slow_echo "╔════════════════════════════════════════╗" 0.01
slow_echo "║     🧠 Néron AI v2.1 — Installateur    ║" 0.01
slow_echo "╚════════════════════════════════════════╝" 0.01
echo -e "${NC}"
echo ""

# --- Vérif dpkg ---
slow_echo "${BLUE}Vérification du gestionnaire de paquets...${NC}" 0.02
if sudo dpkg --configure -a > /dev/null 2>&1; then
    ok "Gestionnaire de paquets OK"
else
    warn "Problème détecté — correction en cours..."
    sudo dpkg --configure -a > /dev/null 2>&1 & spinner $!
    ok "Correction effectuée"
fi

# --- Vérification OS ---
step "1/7" "Vérification du système..."
if ! command -v apt-get >/dev/null 2>&1; then
    fail "Ubuntu/Debian requis"
    exit 1
fi

TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')
if [ "$TOTAL_RAM" -lt 2048 ]; then
    warn "RAM : ${TOTAL_RAM}MB — minimum recommandé 4GB"
    read -p "  Continuer quand même ? [o/N] " CONTINUE
    [ "$CONTINUE" = "o" ] || exit 1
else
    ok "RAM : ${TOTAL_RAM}MB OK"
fi

FREE_DISK=$(df -BG "$HOME" | awk 'NR==2{gsub("G",""); print $4}')
if [ "$FREE_DISK" -lt 10 ]; then
    warn "Disque libre : ${FREE_DISK}GB — minimum recommandé 10GB"
    read -p "  Continuer quand même ? [o/N] " CONTINUE
    [ "$CONTINUE" = "o" ] || exit 1
else
    ok "Disque : ${FREE_DISK}GB libre OK"
fi

# --- Dépendances ---
step "2/7" "Installation des dépendances système..."

PYTHON_VENV_PKG="python3-venv"
python3 --version 2>/dev/null | grep -q "3.12" && PYTHON_VENV_PKG="python3.12-venv" || true

sudo apt-get update -qq > /dev/null 2>&1 & spinner $!
sudo apt-get install -y -qq \
    python3 \
    $PYTHON_VENV_PKG \
    python3-pip \
    python3-yaml \
    git make curl \
    espeak libespeak1 \
    ffmpeg zstd nano > /dev/null 2>&1 & spinner $!
ok "Dépendances OK"

# --- Ollama ---
step "3/7" "Vérification Ollama..."
if ! command -v ollama >/dev/null 2>&1; then
    warn "Ollama non trouvé — installation..."
    curl -fsSL https://ollama.ai/install.sh | sh > /dev/null 2>&1 & spinner $!
    ok "Ollama installé"
else
    ok "Ollama OK ($(ollama --version 2>/dev/null || echo 'version inconnue'))"
fi

if ! systemctl is-active --quiet ollama 2>/dev/null; then
    if systemctl list-unit-files | grep -q ollama; then
        sudo systemctl enable ollama > /dev/null 2>&1
        sudo systemctl start ollama
    else
        ollama serve &
    fi
    ok "Service Ollama démarré"
else
    ok "Ollama déjà actif"
fi

# --- Clone / Update ---
step "4/7" "Récupération de Néron AI..."
if [ -d "$INSTALL_DIR/.git" ]; then
    warn "Dépôt existant — mise à jour..."
    git -C "$INSTALL_DIR" pull origin "$BRANCH" > /dev/null 2>&1 & spinner $!
else
    sudo mkdir -p "$(dirname $INSTALL_DIR)"
    sudo rm -rf "$INSTALL_DIR"
    slow_echo "  Clone : $REPO_URL → $INSTALL_DIR" 0.01
    sudo git clone --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR" > /dev/null 2>&1 & spinner $! || {
        warn "Tentative sans sudo..."
        git clone --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR" > /dev/null 2>&1 & spinner $! || {
            fail "Clone impossible"
            exit 1
        }
    }
    sudo chown -R "$(whoami):$(whoami)" "$INSTALL_DIR"
fi

if [ ! -f "$INSTALL_DIR/Makefile" ]; then
    fail "Échec du clone — Makefile introuvable"
    exit 1
fi
ok "Dépôt OK"

# --- Configuration neron.yaml ---
step "5/7" "Configuration neron.yaml..."
if [ ! -f "$YAML_FILE" ]; then
    cp "$INSTALL_DIR/neron.yaml.example" "$YAML_FILE"
    warn "neron.yaml créé depuis l'exemple — pensez à le configurer"
else
    ok "neron.yaml existant conservé"
fi

# --- Make install ---
step "6/7" "Installation via Makefile..."
make -C "$INSTALL_DIR" install

# --- Modèle Ollama ---
step "7/7" "Modèle Ollama..."
CURRENT_MODEL=$(yaml_get "$YAML_FILE" "llm" "model")
CURRENT_MODEL="${CURRENT_MODEL:-llama3.2:1b}"

if ollama list 2>/dev/null | grep -q "$CURRENT_MODEL"; then
    ok "Modèle $CURRENT_MODEL déjà présent"
else
    warn "Modèle $CURRENT_MODEL non trouvé"
    read -p "  Télécharger maintenant ? [O/n] " DL
    if [ "$DL" != "n" ]; then
        ollama pull "$CURRENT_MODEL" > /dev/null 2>&1 & spinner $!
        ok "Modèle $CURRENT_MODEL prêt"
    fi
fi

# --- Telegram ---
setup_telegram

# --- Résumé ---
echo ""
echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
slow_echo "  ✅ Installation terminée !" 0.03
echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
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
echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
