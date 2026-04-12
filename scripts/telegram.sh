#!/usr/bin/env bash
# scripts/telegram.sh

set -e
clear

# =========================
# COLORS
# =========================
BOLD="\033[1m"
BLUE="\033[34m"
YELLOW="\033[33m"
GREEN="\033[32m"
NC="\033[0m"

# =========================
# UI FUNCTIONS
# =========================
slow_echo() {
    local text="$1"
    local delay="${2:-0.02}"
    for ((i=0; i<${#text}; i++)); do
        printf "%s" "${text:$i:1}"
        sleep $delay
    done
    echo
}

spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='|/-\\'
    while ps -p "$pid" > /dev/null 2>&1; do
        local temp=${spinstr#?}
        printf " [%c]  " "${spinstr}"
        spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "      \b\b\b\b\b\b"
}

echo ""
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  📱 Configuration Telegram"
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

read -p "  Voulez-vous utiliser Telegram ? [O/n] " USE_TG
if [ "$USE_TG" = "n" ]; then
    echo -e "${YELLOW}  👉 Vous pourrez configurer Telegram plus tard${NC}"
    exit 0
fi

echo ""
read -p "  Avez-vous un compte Telegram ? [O/n] " HAS_TG
if [ "$HAS_TG" = "n" ]; then
    echo ""
    echo -e "${YELLOW}  📲 Créez un compte sur https://telegram.org${NC}"
    echo -e "${YELLOW}  Puis relancez ce script${NC}"
    exit 0
fi

echo ""
read -p "  Avez-vous déjà un token de bot ? [O/n] " HAS_TOKEN
if [ "$HAS_TOKEN" = "n" ]; then
    echo ""
    echo -e "${BOLD}  Comment créer un bot Telegram :${NC}"
    echo ""
    echo -e "  1. Ouvrez Telegram et cherchez @BotFather"
    echo -e "  2. Envoyez la commande : /newbot"
    echo -e "  3. Choisissez un nom pour votre bot"
    echo -e "  4. Choisissez un username (doit finir par 'bot')"
    echo -e "  5. Copiez le token fourni"
    echo ""
    read -p "  Appuyez sur Entrée quand vous avez votre token..." _
fi

echo ""
read -p "  Token du bot principal (conversations) : " BOT_TOKEN
if [ -z "$BOT_TOKEN" ]; then
    echo "❌ Token vide"
    exit 1
fi

echo ""
echo -e "${YELLOW}  Récupération automatique du Chat ID...${NC}"
echo -e "${YELLOW}  → Envoyez un message à votre bot maintenant${NC}"
read -p "  Appuyez sur Entrée après avoir envoyé un message..." _

TG_RESPONSE=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getUpdates")

CHAT_ID=$(echo "$TG_RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
updates = data.get('result', [])
print(updates[-1]['message']['chat']['id'] if updates else '')
" 2>/dev/null || echo "")

if [ -z "$CHAT_ID" ]; then
    echo -e "${YELLOW}  ⚠ Impossible de récupérer le Chat ID automatiquement${NC}"
    read -p "  Entrez votre Chat ID manuellement : " CHAT_ID
else
    echo -e "${GREEN}  ✔ Chat ID récupéré : $CHAT_ID${NC}"
fi

echo ""
echo -e "${GREEN}  ✔ Configuration Telegram prête${NC}"
echo "  BOT_TOKEN=$BOT_TOKEN"
echo "  CHAT_ID=$CHAT_ID"
echo ""
