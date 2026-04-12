#!/bin/bash
# ha_install.sh v1.0 - NERON HOME ASSISTANT CORE
set -euo pipefail
clear

# =========================
# COLORS
# =========================
BOLD=$(tput bold)
RESET=$(tput sgr0)
RED=$(tput setaf 1)
GREEN=$(tput setaf 2)
YELLOW=$(tput setaf 3)
BLUE=$(tput setaf 4)
NC=$RESET

# =========================
# CONFIG
# =========================
BASE_DIR="/etc/neron"
HA_DIR="$BASE_DIR/client/homeassistant"
VENV_DIR="$BASE_DIR/server/venv"
HA_USER="eleazar"
SERVICE="neron-homeassistant.service"

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

# =========================
# CHECK SYSTEM
# =========================
slow_echo "${BLUE}Initialisation installation Néron Home Assistant...${NC}"

sudo dpkg --configure -a > /dev/null 2>&1 || true

# =========================
# 1. DEPENDANCES
# =========================
install_dependencies() {
    slow_echo "${BLUE}[1/5] Installation dépendances système...${NC}"

    sudo apt-get update -y -qq > /dev/null 2>&1 &
    spinner $!

    sudo apt-get install -y \
        python3 python3-venv python3-dev \
        libffi-dev libssl-dev \
        build-essential \
        libjpeg-dev zlib1g-dev \
        libopenjp2-7 libtiff6 \
        libturbojpeg0-dev tzdata \
        > /dev/null 2>&1 &
    spinner $!

    echo -e "${GREEN}✔ Dépendances OK${NC}"
}

# =========================
# 2. USER SAFE
# =========================
create_user() {
    slow_echo "${BLUE}[3/5] Vérification utilisateur homeassistant...${NC}"

    GROUPS="dialout"
    getent group i2c >/dev/null && GROUPS="$GROUPS,i2c"
    getent group gpio >/dev/null && GROUPS="$GROUPS,gpio"

    if id "$HA_USER" &>/dev/null; then
        echo "✔ User déjà existant : $HA_USER"

        # sécurise les groupes même si déjà créé
        sudo usermod -aG dialout "$HA_USER" || true
    else
        echo "Création utilisateur : $HA_USER"
        sudo useradd -rm "$HA_USER" -G "$GROUPS"
        echo "✔ User créé"
    fi
}

# =========================
# 3. STRUCTURE
# =========================
setup_directories() {
    slow_echo "${BLUE}[2/5] Création structure Néron...${NC}"

    sudo mkdir -p "$HA_DIR/config"
    sudo chown -R "$HA_USER:$HA_USER" "$HA_DIR"

    echo -e "${GREEN}✔ Dossiers OK${NC}"
}

# =========================
# 4. CHECK VENV
# =========================
check_venv() {
    slow_echo "${BLUE}[4/5] Vérification venv Néron...${NC}"

    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${RED}ERREUR: venv introuvable ($VENV_DIR)${NC}"
        exit 1
    fi

    echo -e "${GREEN}✔ venv OK${NC}"
}

# =========================
# 5. INSTALL HOME ASSISTANT
# =========================
install_ha() {
    slow_echo "${BLUE}[5/5] Installation Home Assistant...${NC}"

    sudo -u "$HA_USER" bash -c "
        source $VENV_DIR/bin/activate &&
        pip install --upgrade pip wheel &&
        pip install homeassistant  &
    " > /dev/null 2>&1 &

    echo -e "${GREEN}✔ Home Assistant installé${NC}"
}

# =========================
# SYSTEMD SERVICE
# =========================
create_service() {
    slow_echo "${BLUE}Création service systemd...${NC}"

    sudo tee /etc/systemd/system/$SERVICE > /dev/null <<EOF
[Unit]
Description=Neron Home Assistant Core
After=network.target

[Service]
Type=simple
User=$HA_USER
WorkingDirectory=$HA_DIR
ExecStart=$VENV_DIR/bin/hass -c $HA_DIR/config
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable $SERVICE

    echo -e "${GREEN}✔ Service systemd OK${NC}"
}

# =========================
# MAIN
# =========================

echo ""
install_dependencies
echo ""
create_user
echo ""
setup_directories
echo ""
check_venv
echo ""
install_ha
echo ""
create_service

echo ""
echo "======================================"
echo -e "${GREEN}✔ INSTALLATION TERMINÉE${NC}"
echo "======================================"
echo "Service : $SERVICE"
echo "URL     : http://100.194.90.109:8123"
echo ""
echo "Commandes :"
echo "  make ha-start"
echo "  make ha-stop"
echo "  make ha-status"
echo ""
