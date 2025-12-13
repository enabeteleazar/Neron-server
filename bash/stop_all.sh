#!/bin/bash

HOMEBOX_DIR="$HOME/homebox"
SERVICES=(
    "_neron/node-red"
    "_neron/n8n"
    "_neron/ollama"
    "_neron/bot"
    "dashboard"
    "monitoring"
    "homeassistant"
    "_nginx-proxy"
    "portainer"
)

echo "🛑 Arrêt de HomeBox..."

for service in "${SERVICES[@]}"; do
    if [ -d "$HOMEBOX_DIR/$service" ]; then
        echo "⏹️  Arrêt de $service..."
        cd "$HOMEBOX_DIR/$service"
        docker compose down
    fi
done

echo "✅ HomeBox arrêté !"
