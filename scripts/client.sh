
#!/usr/bin/env bash
# scripts/client.sh

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
echo -e "  📱 Service Client"
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""


SERVICE="neron-client.service"

usage() {
    echo ""
    echo "Usage:"
    echo "  client.sh start"
    echo "  client.sh stop"
    echo "  client.sh restart"
    echo "  client.sh status"
    echo "  client.sh logs"
    echo ""
    exit 1
}

check_systemd() {
    command -v systemctl >/dev/null 2>&1 || {
        echo "❌ systemctl non disponible"
        exit 1
    }
}

start() {
    echo ""
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "        📱 START NÉRON CLIENT"
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    check_systemd

    sudo systemctl start "$SERVICE"

    sleep 1

    if systemctl is-active --quiet "$SERVICE"; then
        echo -e "${GREEN}✔ Client démarré${NC}"
    else
        echo -e "${RED}❌ Échec démarrage${NC}"
        systemctl status "$SERVICE" --no-pager -l || true
        exit 1
    fi

    echo ""
}

stop() {
    echo ""
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "        🛑 STOP NÉRON CLIENT"
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    check_systemd

    sudo systemctl stop "$SERVICE"

    sleep 1

    if systemctl is-active --quiet "$SERVICE"; then
        echo -e "${RED}❌ Échec arrêt${NC}"
        systemctl status "$SERVICE" --no-pager -l || true
        exit 1
    else
        echo -e "${GREEN}✔ Client arrêté${NC}"
    fi

    echo ""
}

restart() {
    echo ""
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "        🔄 RESTART NÉRON CLIENT"
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    check_systemd

    sudo systemctl restart "$SERVICE"

    sleep 1

    if systemctl is-active --quiet "$SERVICE"; then
        echo -e "${GREEN}✔ Client redémarré${NC}"
    else
        echo -e "${RED}❌ Échec restart${NC}"
        systemctl status "$SERVICE" --no-pager -l || true
        exit 1
    fi

    echo ""
}

status() {
    echo ""
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "        📱 STATUS NÉRON CLIENT"
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    check_systemd

    if systemctl is-active --quiet "$SERVICE"; then
        echo -e "${GREEN}✔ ACTIF${NC}"
    else
        echo -e "${RED}❌ INACTIF${NC}"
    fi

    systemctl status "$SERVICE" --no-pager -l || true

    echo ""
}

logs() {
    echo ""
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "        📜 LOGS NÉRON CLIENT"
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    check_systemd

    journalctl -u "$SERVICE" -f --no-pager || true
}

case "$1" in
    start) start ;;
    stop) stop ;;
    restart) restart ;;
    status) status ;;
    logs) logs ;;
    *) usage ;;
esac
