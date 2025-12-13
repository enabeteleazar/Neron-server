
#!/bin/bash

# ~/homebox/bash/start_all.sh

HOMEBOX_DIR="$HOME/homebox"
SERVICES=(
    "portainer"
    "homeassistant"
    "monitoring"
    "dashboard"
    "_nginx-proxy"
    "_neron/bot"
    "_neron/ollama"
    "_neron/n8n"
    "_neron/node-red"
)

echo "🚀 Démarrage de HomeBox..."

# Créer le réseau s'il n'existe pas
if ! docker network ls | grep -q "Homebox"; then
    echo "📡 Création du réseau Homebox..."
    docker network create Homebox
fi

# Démarrer chaque service
for service in "${SERVICES[@]}"; do
    if [ -d "$HOMEBOX_DIR/$service" ]; then
        echo "▶️  Démarrage de $service..."
        cd "$HOMEBOX_DIR/$service"
        docker compose up -d --build
    else
        echo "⚠️  Dossier $service introuvable"
    fi
done

cd "$HOMEBOX_DIR"
echo "✅ HomeBox démarré !"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
