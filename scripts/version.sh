#!/usr/bin/env bash
# scripts/version.sh

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
        sleep "$delay"
    done
    echo
}

spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='|/-\'
    while ps -p "$pid" > /dev/null 2>&1; do
        local temp=${spinstr#?}
        printf " [%c]  " "${spinstr}"
        spinstr=$temp${spinstr%"$temp"}
        sleep "$delay"
        printf "\b\b\b\b\b\b"
    done
    printf "      \b\b\b\b\b\b"
}

# =========================
# HEADER
# =========================
echo ""
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "        🔍 NÉRON SYSTEM INFO"
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# =========================
# CONFIG
# =========================
API_URL="http://localhost:8010/health"

SERVICES=(
    "neron.service"
    "neron-homeassistant.service"
    "neron-client.service"
)

# =========================
# PYTHON
# =========================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "🐍 PYTHON"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if command -v python3 >/dev/null 2>&1; then
    echo -e "${GREEN}✔ $(python3 --version)${NC}"
    echo "  Path : $(command -v python3)"
else
    echo -e "${RED}❌ Python3 non installé${NC}"
fi

echo ""

# =========================
# API HEALTH
# =========================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "📡 API STATUS"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
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
    print("❌ Réponse API invalide")
    print(raw[:500])
EOF
fi

echo ""

# =========================
# OLLAMA
# =========================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "🤖 OLLAMA"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if command -v ollama >/dev/null 2>&1; then
    echo -e "${GREEN}✔ Ollama installé ($(ollama --version 2>/dev/null))${NC}"
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
# MODELS
# =========================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "🧠 MODELS"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
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
# SERVICES SYSTEMD
# =========================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "⚙️ SERVICES NÉRON"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

for SERVICE in "${SERVICES[@]}"; do
    SERVICE_FILE="/etc/systemd/system/$SERVICE"

    printf "  %-35s" "$SERVICE"

    if [ ! -f "$SERVICE_FILE" ]; then
        echo -e "${YELLOW}⚠ non installé${NC}"
        continue
    fi

    if systemctl is-active --quiet "$SERVICE" 2>/dev/null; then
        echo -e "${GREEN}✔ actif${NC}"
    else
        echo -e "${RED}❌ inactif${NC}"
    fi
done

echo ""

# =========================
# SYSTEM HEALTH
# =========================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "🖥 SYSTEM"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

CPU=$(grep -m1 "model name" /proc/cpuinfo 2>/dev/null | cut -d: -f2)
RAM=$(free -h | awk '/Mem:/ {print $3 "/" $2}')
DISK=$(df -h / | awk 'NR==2 {print $3 "/" $2 " (" $5 ")"}')

echo "CPU   : ${CPU:-unknown}"
echo "RAM   : ${RAM:-unknown}"
echo "DISK  : ${DISK:-unknown}"

echo ""
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "        ${GREEN}✔ FIN${NC}"
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
