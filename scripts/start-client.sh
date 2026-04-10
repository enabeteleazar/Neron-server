#!/usr/bin/env bash

set -e

CLIENT_DIR="/etc/neron/client/mobile"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "        📱 NÉRON CLIENT START (PRO)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# --------------------------------------------------
# CHECK NODE / NPM
# --------------------------------------------------
if ! command -v npm >/dev/null 2>&1; then
    echo "❌ npm non trouvé (Node.js requis)"
    exit 1
fi

# --------------------------------------------------
# CHECK DIRECTORY
# --------------------------------------------------
if [ ! -d "$CLIENT_DIR" ]; then
    echo "❌ Dossier client introuvable : $CLIENT_DIR"
    exit 1
fi

cd "$CLIENT_DIR"

# --------------------------------------------------
# INSTALL DEPENDENCIES
# --------------------------------------------------
if [ ! -d "node_modules" ]; then
    echo "📦 Installation des dépendances..."
    npm install
fi

# --------------------------------------------------
# BUILD CHECK
# --------------------------------------------------
if [ ! -d ".next" ]; then
    echo "⚙️ Build Next.js non trouvé → build en cours..."
    npm run build
else
    echo "✔ Build Next.js déjà présent"
fi

# --------------------------------------------------
# START PRODUCTION SERVER
# --------------------------------------------------
echo ""
echo "🚀 Lancement client en mode PRODUCTION..."
echo "----------------------------------------"

npm start &
