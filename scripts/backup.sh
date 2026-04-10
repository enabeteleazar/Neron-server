#!/usr/bin/env bash

set -e

BASE_DIR="/etc/neron/server"
BACKUP_ROOT="$BASE_DIR/backups"

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
    echo "  backup.sh backup     → crée une sauvegarde"
    echo "  backup.sh restore     → restaure une sauvegarde"
    echo ""
    exit 1
}

# --------------------------------------------------
# BACKUP
# --------------------------------------------------
backup() {
    echo ""
    echo "💾 Sauvegarde de Néron..."
    echo "----------------------------------------"

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

# --------------------------------------------------
# RESTORE
# --------------------------------------------------
restore() {
    echo ""
    echo "📂 Sauvegardes disponibles :"
    echo "----------------------------------------"

    if [ ! -d "$BACKUP_ROOT" ]; then
        echo "❌ Aucune sauvegarde trouvée"
        exit 1
    fi

    BACKUPS=($(ls -1t "$BACKUP_ROOT"))

    for i in "${!BACKUPS[@]}"; do
        echo "  $((i+1))) ${BACKUPS[$i]}"
    done

    echo ""
    read -p "Choisir le numéro de sauvegarde : " CHOICE

    INDEX=$((CHOICE-1))

    SELECTED="${BACKUPS[$INDEX]}"

    if [ -z "$SELECTED" ]; then
        echo "❌ Sélection invalide"
        exit 1
    fi

    SRC="$BACKUP_ROOT/$SELECTED"

    if [ ! -d "$SRC" ]; then
        echo "❌ Dossier introuvable"
        exit 1
    fi

    cp "$SRC/neron.yaml" "$BASE_DIR/neron.yaml"

    if [ -f "$SRC/memory.db" ]; then
        cp "$SRC/memory.db" "$BASE_DIR/data/memory.db"
    fi

    echo "✔ Restauration terminée"
    echo "👉 run: make restart"
    echo ""
}

# --------------------------------------------------
# MAIN
# --------------------------------------------------
case "$1" in
    backup)
        backup
        ;;
    restore)
        restore
        ;;
    *)
        usage
        ;;
esac
