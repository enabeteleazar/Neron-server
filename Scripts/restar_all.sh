#!/bin/bash
# Script pour fixer permissions et relancer les services Homebox

# --- Variables ---
DOCKER_DATA_PATH="/opt/Labo/Data"
PUID=1000
PGID=1000

# --- Dossiers et UID/GID ---
echo "Création et permission des dossiers..."

# Grafana
mkdir -p $DOCKER_DATA_PATH/grafana/data
mkdir -p $DOCKER_DATA_PATH/grafana/provisioning
chown -R 472:472 $DOCKER_DATA_PATH/grafana
chmod -R 755 $DOCKER_DATA_PATH/grafana

# Home Assistant
mkdir -p $DOCKER_DATA_PATH/homeassistant/config
chown -R $PUID:$PGID $DOCKER_DATA_PATH/homeassistant
chmod -R 755 $DOCKER_DATA_PATH/homeassistant

# Node-RED
mkdir -p $DOCKER_DATA_PATH/node-red/data
chown -R $PUID:$PGID $DOCKER_DATA_PATH/node-red
chmod -R 755 $DOCKER_DATA_PATH/node-red

# Prometheus
mkdir -p $DOCKER_DATA_PATH/prometheus/data
mkdir -p $DOCKER_DATA_PATH/prometheus/config
chown -R 65534:65534 $DOCKER_DATA_PATH/prometheus
chmod -R 755 $DOCKER_DATA_PATH/prometheus

# N8N
mkdir -p $DOCKER_DATA_PATH/n8n/data
chown -R $PUID:$PGID $DOCKER_DATA_PATH/n8n
chmod -R 755 $DOCKER_DATA_PATH/n8n

echo "Tous les dossiers et permissions sont prêts."

# --- Relance Docker ---
echo "Relance des conteneurs Homebox..."
docker compose up -d grafana
docker compose up -d homeassistant
docker compose up -d node-red
docker compose up -d prometheus
docker compose up -d n8n

echo "Tous les services ont été relancés."
echo "Vérifie les logs avec : docker logs -f <nom_du_service>"
