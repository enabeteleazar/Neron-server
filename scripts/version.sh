
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
echo -e "  🔍 Info Système Néron"
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# =========================
# CONFIG
# =========================
SERVICES=(
    "neron.service"
    "neron-homeassistant.service"
    "neron-client.service"
)

# =========================
# PYTHON VERSION
# =========================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e " Python"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if command -v python3 >/dev/null 2>&1; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    PYTHON_PATH=$(command -v python3)
    echo -e "${GREEN}✔ $PYTHON_VERSION${NC}"
    echo    "  Path : $PYTHON_PATH"
else
    echo -e "${RED}❌ Python3 non installé${NC}"
fi

echo ""

# =========================
# SERVICES STATUS
# =========================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e " Service Néron "
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
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
