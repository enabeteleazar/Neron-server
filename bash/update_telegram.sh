#!/bin/bash

# ========================================
# HomeBox Update Script with Telegram notifications
# ========================================

set -e

# ---------------------------
# CONFIG TELEGRAM
# ---------------------------
TELEGRAM_BOT_TOKEN="TON_TOKEN_ICI"
TELEGRAM_CHAT_ID="TON_CHAT_ID_ICI"

send_telegram() {
    local MESSAGE=$1
    curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
         -d chat_id="$TELEGRAM_CHAT_ID" \
         -d text="$MESSAGE" \
         -d parse_mode="Markdown" > /dev/null
}

echo "===================================="
echo "🔄 Début de la mise à jour HomeBox"
echo "===================================="

send_telegram "🔄 *HomeBox Update* : Début de la mise à jour des services."

# Définir les services à mettre à jour
SERVICES=("homeassistant" "monitoring/cadvisor" "monitoring/prometheus" "monitoring/grafana" "portainer" "nginx-proxy-manager" "codi-tv" "ollama")

# Fonction pour mettre à jour un service
update_service() {
    local SERVICE_PATH=$1
    echo "------------------------------------"
    echo "🔹 Mise à jour du service: $SERVICE_PATH"
    echo "------------------------------------"
    
    if [ -f "$SERVICE_PATH/docker-compose.yaml" ]; then
        cd "$SERVICE_PATH"
        echo "⬇️  Pull des dernières images..."
        docker compose pull

        echo "🛑 Stop des conteneurs..."
        docker compose down

        echo "🔧 Rebuild si nécessaire..."
        docker compose up -d --build

        echo "✅ Service $SERVICE_PATH mis à jour et relancé"
        cd - >/dev/null
    else
        echo "⚠️  Aucun docker-compose.yaml trouvé pour $SERVICE_PATH, skipping..."
    fi
}

# Boucle sur tous les services
for SERVICE in "${SERVICES[@]}"; do
    update_service "$SERVICE"
done

# Nettoyage des images et volumes inutilisés
echo "🧹 Nettoyage des images et volumes inutilisés..."
docker system prune -af --volumes

echo "===================================="
echo "🎉 Mise à jour HomeBox terminée !"
echo "===================================="

send_telegram "🎉 *HomeBox Update* : Tous les services ont été mis à jour avec succès ! ✅"
