#!/usr/bin/env bash

set -e

CLIENT_DIR="/etc/neron/client/mobile"
LOG_FILE="/var/log/neron-client.log"

BLUE="\033[34m"
GREEN="\033[32m"
YELLOW="\033[33m"
RED="\033[31m"
NC="\033[0m"

# --------------------------------------------------
# HELP
# --------------------------------------------------
usage() {
    echo ""
    echo "Usage:"
    echo "  client.sh start"
    echo "  client.sh stop"
    echo "  client.sh restart"
    echo "  client.sh status"
    echo ""
    exit 1
}

# --------------------------------------------------
# STATUS
# --------------------------------------------------
status() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "        📱 NÉRON CLIENT STATUS"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    if pgrep -f "next start" >/dev/null 2>&1; then
        echo -e "${GREEN}✔ Client actif${NC}"
        echo "PID(s) : $(pgrep -f 'next start')"
    else
        echo -e "${RED}❌ Client arrêté${NC}"
    fi

    echo ""
}

# --------------------------------------------------
# START
# --------------------------------------------------
start() {
set -e

CLIENT_DIR="/etc/neron/client/mobile"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "        📱 NÉRON CLIENT START (PRO)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# --------------------------------------------------
# CHECK NODE
# --------------------------------------------------
if ! command -v npm >/dev/null 2>&1; then
    echo "❌ npm non trouvé"
    exit 1
fi

cd "$CLIENT_DIR"

# --------------------------------------------------
# INSTALL DEPENDENCIES
# --------------------------------------------------
if [ ! -d "node_modules" ]; then
    echo "📦 npm install..."
    npm install
fi

# --------------------------------------------------
# STRONG BUILD VALIDATION
# --------------------------------------------------
echo "🔍 Vérification build Next.js..."

if [ ! -f ".next/BUILD_ID" ]; then
    echo "⚠ Build invalide détecté → rebuild forcé"
    rm -rf .next
    npm run build
else
    echo "✔ Build Next.js valide"
fi

# --------------------------------------------------
# START
# --------------------------------------------------
echo ""
echo "🚀 Lancement production..."
echo "----------------------------------------"

npm start &
}

# --------------------------------------------------
# STOP
# --------------------------------------------------
stop() {
set -e

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "        🛑 STOP NÉRON CLIENT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# --------------------------------------------------
# METHOD 1: PORT KILL (BEST)
# --------------------------------------------------
if command -v fuser >/dev/null 2>&1; then
    echo "🔍 Arrêt via port 3000..."
    fuser -k 3000/tcp >/dev/null 2>&1 || true
fi

# --------------------------------------------------
# METHOD 2: FALLBACK PROCESS KILL
# --------------------------------------------------
echo "🔍 Nettoyage processus Next.js..."

pkill -f "next start" >/dev/null 2>&1 || true
pkill -f "node.*next" >/dev/null 2>&1 || true
pkill -f "next"       >/dev/null 2>&1 || true

# --------------------------------------------------
# VERIFICATION
# --------------------------------------------------
sleep 1

if pgrep -f "next start" >/dev/null 2>&1; then
    echo "⚠ Certains processus restent actifs"
else
    echo "✔ Client Néron arrêté"
fi

echo ""

}

# --------------------------------------------------
# RESTART
# --------------------------------------------------
restart() {
    stop
    sleep 1
    start
}

# --------------------------------------------------
# MAIN
# --------------------------------------------------
case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    *)
        usage
        ;;
esac
