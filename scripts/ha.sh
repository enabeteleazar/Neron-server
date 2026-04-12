#!/usr/bin/env bash
set -e

BASE_DIR="/etc/neron"
REPO_DIR="$BASE_DIR/server"
SERVICE="neron-homeassistant.service"
CONFIG_FILE="$REPO_DIR/neron.yaml"
PYTHON="$BASE_DIR/server/venv/bin/python3"

BLUE="\033[34m"
GREEN="\033[32m"
YELLOW="\033[33m"
RED="\033[31m"
NC="\033[0m"

usage() {
    echo ""
    echo "Usage:"
    echo "  ha.sh start"
    echo "  ha.sh stop"
    echo "  ha.sh restart"
    echo "  ha.sh config"
    echo "  ha.sh status"
    echo "  ha.sh logs"
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
    echo "        📱 START HOME ASSISTANT"
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
    echo "        🛑 STOP HOME ASSISTANT"
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
    echo "        🔄 RESTART HOME ASSISTANT"
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
    echo "        📱 STATUS HOMEASSISTANT"
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
    echo "        📜 LOGS HOME ASSISTANT"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    check_systemd

    journalctl -u "$SERVICE" -f --no-pager || true
}

config() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "        📜 CONFIG HOME ASSISTANT"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    CURRENT_URL=$($PYTHON -c "import yaml; d=yaml.safe_load(open('$CONFIG_FILE')); print(d.get('home_assistant',{}).get('url','http://homeassistant.local:8123'))")
    CURRENT_ENABLED=$($PYTHON -c "import yaml; d=yaml.safe_load(open('$CONFIG_FILE')); print(d.get('home_assistant',{}).get('enabled',False))")
    CURRENT_TOKEN=$($PYTHON -c "import yaml; d=yaml.safe_load(open('$CONFIG_FILE')); print(d.get('home_assistant',{}).get('token',''))")

    echo "  État actuel  : $CURRENT_ENABLED"
    echo "  URL actuelle : $CURRENT_URL"
    echo ""

    read -p "  URL Home Assistant [$CURRENT_URL] : " HA_URL
    HA_URL=${HA_URL:-$CURRENT_URL}

    echo ""
    echo "  👉 Génère un token dans HA"
    echo ""

    read -p "  Token (laisser vide pour garder l'actuel) : " HA_TOKEN
    HA_TOKEN=${HA_TOKEN:-$CURRENT_TOKEN}

    echo ""
    echo "🔍 Test de connexion..."

    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer $HA_TOKEN" \
        "$HA_URL/api/")

    if [ "$HTTP_CODE" = "200" ]; then
        echo "✔ Connexion OK"

        $PYTHON - <<EOF
import yaml

config_file = "$CONFIG_FILE"
url = "$HA_URL"
token = "$HA_TOKEN"

with open(config_file, "r") as f:
    config = yaml.safe_load(f) or {}

config.setdefault("home_assistant", {})
config["home_assistant"]["enabled"] = True
config["home_assistant"]["url"] = url
config["home_assistant"]["token"] = token

with open(config_file, "w") as f:
    yaml.dump(config, f, allow_unicode=True)

print("✔ neron.yaml mis à jour")
EOF

        echo ""
        read -p "  Redémarrer Néron maintenant ? [O/n] " RESTART

        if [ "$RESTART" != "n" ]; then
            make -C "$REPO_DIR" restart
        else
            echo "  👉 Lance : make restart"
        fi

    else
        echo "❌ Connexion échouée ($HTTP_CODE)"
        exit 1
    fi
}

case "$1" in
    start) start ;;
    stop) stop ;;
    restart) restart ;;
    status) status ;;
    logs) logs ;;
    config) config ;;
    *) usage ;;
esac
