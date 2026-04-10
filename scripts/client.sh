#!/usr/bin/env bash
set -e

SERVICE="neron-client.service"

BLUE="\033[34m"
GREEN="\033[32m"
YELLOW="\033[33m"
RED="\033[31m"
NC="\033[0m"

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
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "        📱 START NÉRON CLIENT"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
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
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "        🛑 STOP NÉRON CLIENT"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
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
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "        🔄 RESTART NÉRON CLIENT"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
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
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "        📱 STATUS NÉRON CLIENT"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
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
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "        📜 LOGS NÉRON CLIENT"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
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
