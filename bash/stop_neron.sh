#!/bin/bash
#!/bin/bash
# Script d'extinction de la stack Néron
# Chemin : /homebox/stop_neron.sh

ROOT="/home/eleazar/homebox"
ENV_FILE="$ROOT/.env"
NERON_DIR="$ROOT/services/neron"

echo "======================================"
echo "        🚀 Extinction de NÉRON"
echo "======================================"

start_stack() {
    NAME=$1
    COMPOSE_PATH=$2

    echo ""
    echo "➡️  LArrêt de $NAME ..."
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_PATH" down

    if [ $? -ne 0 ]; then
        echo "❌ Erreur lors du démarrage de $NAME"
        exit 1
    fi

    echo "✅ $NAME démarré"
}

# ORDRE LOGIQUE
# 1. neron-core
start_stack "neron-core" "$NERON_DIR/neron-core/docker-compose.yaml"

# 2. ollama
start_stack "ollama" "$NERON_DIR/ollama/docker-compose.yaml"

# 3. neron-telegram
start_stack "neron-telegram" "$NERON_DIR/neron-telegram/docker-compose.yaml"

# 4. node-red
start_stack "node-red" "$NERON_DIR/node-red/docker-compose.yaml"

# 5. n8n
start_stack "n8n" "$NERON_DIR/n8n/docker-compose.yaml"

echo ""
echo "======================================"
echo "  ✅ Tous les services Néron sont FF"
echo "======================================"
echo ""

docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

