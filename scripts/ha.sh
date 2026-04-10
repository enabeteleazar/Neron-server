#!/usr/bin/env bash

set -e

BASE_DIR="/etc/neron"
REPO_DIR="$BASE_DIR/server"
PYTHON="$BASE_DIR/server/venv/bin/python3"
CONFIG_FILE="$REPO_DIR/neron.yaml"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🏠 Configuration Home Assistant"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Récupération config actuelle
CURRENT_URL=$($PYTHON -c "import yaml; d=yaml.safe_load(open('$CONFIG_FILE')); print(d.get('home_assistant',{}).get('url','http://homeassistant.local:8123'))")
CURRENT_ENABLED=$($PYTHON -c "import yaml; d=yaml.safe_load(open('$CONFIG_FILE')); print(d.get('home_assistant',{}).get('enabled',False))")
CURRENT_TOKEN=$($PYTHON -c "import yaml; d=yaml.safe_load(open('$CONFIG_FILE')); print(d.get('home_assistant',{}).get('token',''))")

echo "  État actuel  : $CURRENT_ENABLED"
echo "  URL actuelle : $CURRENT_URL"
echo ""

# Input utilisateur
read -p "  URL Home Assistant [$CURRENT_URL] : " HA_URL
HA_URL=${HA_URL:-$CURRENT_URL}

echo ""
echo "  👉 Générez un token dans HA :"
echo "     Profil → Sécurité → Tokens d'accès longue durée"
echo ""

read -p "  Token (laisser vide pour garder l'actuel) : " HA_TOKEN
HA_TOKEN=${HA_TOKEN:-$CURRENT_TOKEN}

echo ""
echo "🔍 Test de connexion vers $HA_URL..."

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $HA_TOKEN" \
    "$HA_URL/api/")

if [ "$HTTP_CODE" = "200" ]; then
    echo "✔ Connexion réussie (HTTP $HTTP_CODE)"

    $PYTHON "$REPO_DIR/scripts/ha_setup.py" "$CONFIG_FILE" "$HA_URL" "$HA_TOKEN"

    echo ""
    read -p "  Redémarrer Néron maintenant ? [O/n] " RESTART

    if [ "$RESTART" != "n" ]; then
        make -C "$REPO_DIR" restart
    else
        echo "  👉 Lance : make restart quand tu es prêt"
    fi
else
    echo "❌ Connexion échouée (HTTP $HTTP_CODE)"
    echo "  Vérifie l'URL et le token — neron.yaml non modifié"
    exit 1
fi

echo ""
