#!/usr/bin/env bash
# scripts/backup.sh

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
echo -e "  💾 Backup Néron"
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# =========================
# CONFIG
# =========================
BASE_DIR="/etc/neron/server"
BACKUP_ROOT="$BASE_DIR/backups"

# =========================
# USAGE
# =========================
usage() {
    echo ""
    echo "Usage:"
    echo "  backup.sh backup"
    echo "  backup.sh restore"
    echo ""
    exit 1
}

# =========================
# BACKUP
# =========================
backup() {
    echo ""
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "        💾 BACKUP NÉRON"
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    DEST="$BACKUP_ROOT/$TIMESTAMP"

    mkdir -p "$DEST"

    cp "$BASE_DIR/neron.yaml" "$DEST/neron.yaml"

    if [ -f "$BASE_DIR/data/memory.db" ]; then
        cp "$BASE_DIR/data/memory.db" "$DEST/memory.db"
    fi

    echo -e "${GREEN}✔ Sauvegarde créée : $DEST${NC}"
    echo ""
}

# =========================
# RESTORE
# =========================
restore() {
    echo ""
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "        📂 RESTORE NÉRON"
    echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    if [ ! -d "$BACKUP_ROOT" ]; then
        echo -e "${RED}❌ Aucune sauvegarde trouvée${NC}"
        exit 1
    fi

    echo "Sauvegardes disponibles :"
    echo ""

    BACKUPS=($(ls -1t "$BACKUP_ROOT"))

    for i in "${!BACKUPS[@]}"; do
        echo "  $((i+1))) ${BACKUPS[$i]}"
    done

    echo ""
    read -p "Choisir le numéro de sauvegarde : " CHOICE

    INDEX=$((CHOICE-1))
    SELECTED="${BACKUPS[$INDEX]}"

    if [ -z "$SELECTED" ]; then
        echo -e "${RED}❌ Sélection invalide${NC}"
        exit 1
    fi

    SRC="$BACKUP_ROOT/$SELECTED"

    if [ ! -d "$SRC" ]; then
        echo -e "${RED}❌ Dossier introuvable${NC}"
        exit 1
    fi

    cp "$SRC/neron.yaml" "$BASE_DIR/neron.yaml"

    if [ -f "$SRC/memory.db" ]; then
        cp "$SRC/memory.db" "$BASE_DIR/data/memory.db"
    fi

    echo -e "${GREEN}✔ Restauration terminée${NC}"
    echo "👉 run: make restart"
    echo ""
}

case "$1" in
    backup)  backup ;;
    restore) restore ;;
    *)       usage ;;
esac
