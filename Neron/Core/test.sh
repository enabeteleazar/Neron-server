#!/bin/bash

# Script de test pour neron-core
# Chemin : /home/eleazar/homebox/services/neron/neron-core/neron-core_test.sh

NERON_CORE_URL="http://localhost:4000"
CONTAINER_NAME="neron-core"
COMPOSE_PATH="/home/eleazar/homebox/services/neron/neron-core/docker-compose.yaml"
ENV_FILE="/home/eleazar/homebox/.env"

# Couleurs pour l’affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "======================================"
echo "   🧪 Test de neron-core"
echo "======================================"
echo ""

# active le venv
source venv/bin/activate

# Verification rapide
python3 -c "import fastapi" || {
     echo -e "${RED}Erreur: fastapi n'est pas installé dans le venv.${NC}"
     exit 1
}

# Lancement de main.py
python3 -m neron.neron_core.main &
PID=$!

# Attendre que le serveur démarre
echo -e "${GREEN}Attente du démarrage du serveur neron-core...${NC}"
sleep 5

# Verifier que le serveur tourne
echo -e "${BLUE}Verification du statut du service neron-core...${NC}"
curl -s http://localhost:4000/health | grep status

# Test du endpoint /chat
echo -e "${BLUE}Test du endpoint /chat...${NC}"
curl -s -X POST http://localhost:4000/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Bonjour Néron."}' | jq .

# Stop le serveur
echo -e "${YELLOW}\nArrêt du serveur neron-core...${NC}"
kill $PID
wait $PID 2>/dev/null
echo -e "\n Test terminé."