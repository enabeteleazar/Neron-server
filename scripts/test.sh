#!/usr/bin/env bash
# scripts/test.sh

set -e
clear

# =========================
# COLORS
# =========================
BOLD="\033[1m"
BLUE="\033[34m"
YELLOW="\033[33m"
GREEN="\033[32m"
RED="\033[31m"
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
echo -e "  🧪 Néron Test System"
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# =========================
# CONFIG
# =========================
API_URL="http://localhost:8010/health"

# =========================
# [1/3] API STATUS
# =========================
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "📡 API STATUS"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

HTTP_CODE=$(curl -s -o /tmp/neron_api.json -w "%{http_code}" "$API_URL" || true)
API_RESPONSE=$(cat /tmp/neron_api.json 2>/dev/null || true)

if [ "$HTTP_CODE" != "200" ]; then
    echo -e "${RED}❌ API HTTP $HTTP_CODE${NC}"
else
    echo "$API_RESPONSE" | python3 - << 'EOF'
import sys, json

raw = sys.stdin.read().strip()

try:
    data = json.loads(raw)
    print(f"✔ Status   : {data.get('status','unknown')}")
    print(f"✔ Version  : {data.get('version','unknown')}")
except Exception:
    print("❌ Réponse API invalide (non JSON)")
    print("\n--- RAW RESPONSE ---")
    print(raw[:500])
EOF
fi

echo ""

# =========================
# [2/3] OLLAMA STATUS
# =========================
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "🤖 OLLAMA STATUS"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if command -v ollama >/dev/null 2>&1; then
    VERSION=$(ollama --version 2>/dev/null || echo "version inconnue")
    echo -e "${GREEN}✔ Ollama installé (${VERSION})${NC}"
else
    echo -e "${RED}❌ Ollama absent${NC}"
fi

if systemctl is-active --quiet ollama 2>/dev/null; then
    echo -e "${GREEN}✔ Service actif${NC}"
else
    echo -e "${YELLOW}⚠ Service inactif${NC}"
fi

echo ""

# =========================
# [3/3] MODELS
# =========================
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "🧠 MODELS AVAILABLE"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if command -v ollama >/dev/null 2>&1; then
    MODELS=$(ollama list 2>/dev/null | awk 'NR>1 {print $1}')

    if [ -n "$MODELS" ]; then
        while read -r model; do
            echo -e "${GREEN}✔ $model${NC}"
        done <<< "$MODELS"
    else
        echo -e "${YELLOW}⚠ Aucun modèle trouvé${NC}"
    fi
else
    echo -e "${RED}❌ Ollama non disponible${NC}"
fi

echo ""

# =========================
# SYSTEM HEALTH
# =========================
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "🖥  SYSTEM HEALTH"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

CPU=$(grep -m1 "model name" /proc/cpuinfo 2>/dev/null | cut -d: -f2)
RAM=$(free -h | awk '/Mem:/ {print $3 "/" $2}')
DISK=$(df -h / | awk 'NR==2 {print $3 "/" $2 " (" $5 ")"}')

echo "CPU   : ${CPU:-unknown}"
echo "RAM   : ${RAM:-unknown}"
echo "DISK  : ${DISK:-unknown}"

echo ""
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "        ${GREEN}✔ TEST TERMINÉ${NC}"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
