#!/usr/bin/env bash
# scripts/ha.sh

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
echo -e "   Home Assistant Manager"
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# =========================
# CONFIG
# =========================
BASE_DIR="/etc/neron"
REPO_DIR="$BASE_DIR"
SERVICE="neron-homeassistant.service"
CONFIG_FILE="$REPO_DIR/neron.yaml"
PYTHON="$BASE_DIR/venv/bin/python3"

# =========================
# USAGE
# =========================
usage() {
    echo ""
    echo "Usage:"
    echo "  ha.sh start"
    echo "  ha.sh stop"
    echo "  ha.sh restart"
    echo "  ha.sh status"
    echo "  ha.sh logs"
    echo "  ha.sh config"
    echo ""
    exit 1
}

# =========================
# HELPERS
# =========================
check_systemd() {
    command -v systemctl >/dev/null 2>&1 || {
        echo " systemctl non disponible"
        exit 1
    }
}

# =========================
# COMMANDS
# =========================
start() {
    echo ""
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "         START HOME ASSISTANT"
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    check_systemd

    sudo systemctl start "$SERVICE"

    sleep 1

    if systemctl is-active --quiet "$SERVICE"; then
        echo -e "${GREEN} Home Assistant démarré${NC}"
    else
        echo -e "${RED} Échec démarrage${NC}"
        systemctl status "$SERVICE" --no-pager -l || true
        exit 1
    fi

    echo ""
}

stop() {
    echo ""
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "        STOP HOME ASSISTANT"
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    check_systemd

    sudo systemctl stop "$SERVICE"

    sleep 1

    if systemctl is-active --quiet "$SERVICE"; then
        echo -e "${RED} Échec arrêt${NC}"
        systemctl status "$SERVICE" --no-pager -l || true
        exit 1
    else
        echo -e "${GREEN} Home Assistant arrêté${NC}"
    fi

    echo ""
}

restart() {
    echo ""
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "         RESTART HOME ASSISTANT"
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    check_systemd

    sudo systemctl restart "$SERVICE"

    sleep 1

    if systemctl is-active --quiet "$SERVICE"; then
        echo -e "${GREEN} Home Assistant redémarré${NC}"
    else
        echo -e "${RED} Échec restart${NC}"
        systemctl status "$SERVICE" --no-pager -l || true
        exit 1
    fi

    echo ""
}

status() {
    echo ""
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "         STATUS HOME ASSISTANT"
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    check_systemd

    if systemctl is-active --quiet "$SERVICE"; then
        echo -e "${GREEN} ACTIF${NC}"
    else
        echo -e "${RED} INACTIF${NC}"
    fi

    systemctl status "$SERVICE" --no-pager -l || true

    echo ""
}

logs() {
    echo ""
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "         LOGS HOME ASSISTANT"
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    check_systemd

    journalctl -u "$SERVICE" -f --no-pager || true
}

config() {
    echo ""
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "          CONFIG HOME ASSISTANT"
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
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
    echo "   Génère un token dans HA"
    echo ""

    read -p "  Token (laisser vide pour garder l'actuel) : " HA_TOKEN
    HA_TOKEN=${HA_TOKEN:-$CURRENT_TOKEN}

    echo ""
    echo " Test de connexion..."

    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer $HA_TOKEN" \
        "$HA_URL/api/")

    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "${GREEN} Connexion OK${NC}"

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

print("neron.yaml mis à jour")
EOF

        echo ""
        read -p "Redémarrer Néron maintenant ? [O/n] " RESTART_NOW

        if [ "$RESTART_NOW" != "n" ]; then
            make -C "$REPO_DIR" restart
        else
            echo "Lance : make restart"
        fi

    else
        echo -e "${RED}Connexion échouée ($HTTP_CODE)${NC}"
        exit 1
    fi

    echo ""
}

case "$1" in
    start)   start ;;
    stop)    stop ;;
    restart) restart ;;
    status)  status ;;
    logs)    logs ;;
    config)  config ;;
    *)       usage ;;
esac
