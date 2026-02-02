#!/bin/bash
# ==========================================
# Réorganisation Neron_AI vers arborescence propre
# ==========================================

NERON_DIR="/opt/Neron_AI"

echo "[INFO] Réorganisation Neron_AI..."

# ─── 1. Déplacer backend/core → neron-core
if [ -d "$NERON_DIR/backend/core" ]; then
    echo "[INFO] Déplacement backend/core → neron-core"
    mv "$NERON_DIR/backend/core" "$NERON_DIR/neron-core"
fi

# ─── 2. Déplacer backend/memory → neron-core/memory si pas déjà présent
if [ -d "$NERON_DIR/backend/memory" ]; then
    echo "[INFO] Déplacement backend/memory → neron-core/memory"
    mv "$NERON_DIR/backend/memory" "$NERON_DIR/neron-core/memory"
fi

# ─── 3. Déplacer backend/llm → modules/neron-llm
if [ -d "$NERON_DIR/backend/llm" ]; then
    echo "[INFO] Déplacement backend/llm → modules/neron-llm"
    mkdir -p "$NERON_DIR/modules/neron-llm"
    mv "$NERON_DIR/backend/llm"/* "$NERON_DIR/modules/neron-llm/"
fi

# ─── 4. Déplacer backend/search → modules/neron-search
if [ -d "$NERON_DIR/backend/search" ]; then
    echo "[INFO] Déplacement backend/search → modules/neron-search"
    mkdir -p "$NERON_DIR/modules/neron-search"
    mv "$NERON_DIR/backend/search"/* "$NERON_DIR/modules/neron-search/"
fi

# ─── 5. Déplacer backend/stt → modules/neron-stt
if [ -d "$NERON_DIR/backend/stt" ]; then
    echo "[INFO] Déplacement backend/stt → modules/neron-stt"
    mkdir -p "$NERON_DIR/modules/neron-stt"
    mv "$NERON_DIR/backend/stt"/* "$NERON_DIR/modules/neron-stt/"
fi

# ─── 6. Déplacer docker-compose.yaml et docker/ → docker/
echo "[INFO] Déplacement docker-compose et docker/ → docker/"
mkdir -p "$NERON_DIR/docker"
mv "$NERON_DIR/docker-compose.yaml" "$NERON_DIR/docker/"
if [ -d "$NERON_DIR/docker" ]; then
    mv "$NERON_DIR/docker/requirements.txt" "$NERON_DIR/docker/"
fi

# ─── 7. Déplacer neron-data → data
if [ -d "$NERON_DIR/neron-data" ]; then
    echo "[INFO] Déplacement neron-data → data"
    mv "$NERON_DIR/neron-data"/* "$NERON_DIR/data/"
    rmdir "$NERON_DIR/neron-data"
fi

# ─── 8. Déplacer frontend/hud, web, telegram → frontend/
if [ -d "$NERON_DIR/frontend/hud" ] || [ -d "$NERON_DIR/frontend/web" ] || [ -d "$NERON_DIR/frontend/telegram" ]; then
    echo "[INFO] Réorganisation frontend"
    mkdir -p "$NERON_DIR/frontend"
    [ -d "$NERON_DIR/frontend/hud" ] && mv "$NERON_DIR/frontend/hud" "$NERON_DIR/frontend/"
    [ -d "$NERON_DIR/frontend/web" ] && mv "$NERON_DIR/frontend/web" "$NERON_DIR/frontend/"
    [ -d "$NERON_DIR/frontend/telegram" ] && mv "$NERON_DIR/frontend/telegram" "$NERON_DIR/frontend/"
fi

# ─── 9. Supprimer backend vide
if [ -d "$NERON_DIR/backend" ]; then
    rmdir "$NERON_DIR/backend" 2>/dev/null
fi

echo "[INFO] Réorganisation terminée !"
tree -L 4 "$NERON_DIR"
