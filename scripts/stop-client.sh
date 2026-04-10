#!/usr/bin/env bash

set -e

CLIENT_DIR="/etc/neron/client/mobile"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "        🛑 STOP NÉRON CLIENT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# --------------------------------------------------
# METHOD 1: PM2 (if used later)
# --------------------------------------------------
if command -v pm2 >/dev/null 2>&1; then
    if pm2 list | grep -q neron-client; then
        echo "🧠 Arrêt via PM2..."
        pm2 stop neron-client
        pm2 delete neron-client
        echo "✔ Client arrêté (PM2)"
        exit 0
    fi
fi

# --------------------------------------------------
# METHOD 2: KILL NODE PROCESS (Next.js)
# --------------------------------------------------
echo "🔍 Recherche processus Next.js..."

PIDS=$(pgrep -f "next start" || true)

if [ -z "$PIDS" ]; then
    echo "⚠ Aucun client Next.js trouvé"
    exit 0
fi

echo "🛑 Arrêt des processus : $PIDS"
kill -9 $PIDS

echo "✔ Client Néron arrêté"
echo ""
