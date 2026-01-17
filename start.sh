#!/bin/bash

# Fichier .env
ENV_FILE="/opt/Labo/Env/.env"

# Dossier contenant tous les services
SERVICES_DIR="/opt/Labo/Services"

# Liste des services à lancer (nom des sous-dossiers)
SERVICES=(
	"Beszel"
	"Cadvisor"
	"dashboard"
	"Dashboard"
	"Grafana"
	"HomeAssistant"
  	"n8n"
	"NginxProxy"
	"Node-Red"
	"Portainer"
	"Prometheus"
)

# Boucle sur chaque service de la liste pour Build.
for Service in "${SERVICES[@]}"; do
    COMPOSE_FILE="$SERVICES_DIR/$Service/docker-compose.yaml"

    if [ -f "$COMPOSE_FILE" ]; then
        echo "--------------------------------------"
        echo "Lancement du service : $Service"
        echo "Fichier compose : $COMPOSE_FILE"
        echo "--------------------------------------"

        # Lancement du build et env-file
        docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" build

        if [ $? -eq 0 ]; then
            echo "✅ Service $Service build avec succès."
        else
            echo "❌ Échec build du service $Service."
        fi
    else
        echo "⚠️ Fichier docker-compose.yaml introuvable pour $Service"
    fi
done

# Boucle sur chaque service de la liste
for Service in "${SERVICES[@]}"; do
    COMPOSE_FILE="$SERVICES_DIR/$Service/docker-compose.yaml"

    if [ -f "$COMPOSE_FILE" ]; then
        # Lancement du conteneur avec build et env-file
        docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d

        if [ $? -eq 0 ]; then    
            echo "✅ Service $Service build avec succès."
        else
            echo "❌ Échec build du service $Service."
        fi
    else  
        echo "⚠ Fichier docker-compose.yaml introuvable pour $Service"
    fi
done


echo "--------------------------------------"
echo "Tous les services de la liste ont été traités."

