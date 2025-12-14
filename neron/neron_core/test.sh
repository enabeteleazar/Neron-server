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

# Fonction pour afficher les résultats
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
    fi
}

# Fonction pour tester un endpoint
test_endpoint() {
    local endpoint=$1
    local description=$2

    echo -e "${BLUE}➡️  Test: $description${NC}"
    response=$(curl -s -w "\n%{http_code}" "$NERON_CORE_URL$endpoint")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" = "200" ]; then
        print_result 0 "$description"
        echo "   Réponse: $body"
    else
        print_result 1 "$description (HTTP $http_code)"
        echo "   Réponse: $body"
    fi
    echo ""
}

# 1. Vérifier si Docker est accessible
echo -e "${YELLOW}[1/8] Vérification de Docker…${NC}"
if docker ps > /dev/null 2>&1; then
    print_result 0 "Docker est accessible"
else
    print_result 1 "Docker n’est pas accessible"
    exit 1
fi
echo ""

# 2. Rebuild et redémarrage
echo -e "${YELLOW}[2/8] Rebuild et redémarrage du container…${NC}"
cd /home/eleazar/homebox/services/neron/neron-core || {
    echo "Erreur: impossible d’accéder au dossier"
    echo "Vérifie le chemin dans le script (ligne 7)"
    exit 1
}

docker compose --env-file "$ENV_FILE" down
docker compose --env-file "$ENV_FILE" up -d --build

if [ $? -eq 0 ]; then
    print_result 0 "Container redémarré"
else
    print_result 1 "Erreur lors du redémarrage"
    exit 1
fi
echo ""

# 3. Attendre que le service démarre
echo -e "${YELLOW}[3/8] Attente du démarrage (15 secondes)…${NC}"
sleep 15
echo ""

# 4. Vérifier si le container est UP
echo -e "${YELLOW}[4/8] Vérification du statut du container…${NC}"
container_status=$(docker ps --filter "name=$CONTAINER_NAME" --format "{{.Status}}")

if [ -n "$container_status" ]; then
    print_result 0 "Container UP: $container_status"
else
    print_result 1 "Container DOWN ou introuvable"
    echo "Logs du container:"
    docker logs "$CONTAINER_NAME" --tail 50
    exit 1
fi
echo ""

# 5. Vérifier le healthcheck (si présent)
echo -e "${YELLOW}[5/8] Vérification du healthcheck…${NC}"
health_status=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null)

if [ "$health_status" = "healthy" ]; then
    print_result 0 "Healthcheck: healthy"
elif [ "$health_status" = "starting" ]; then
    echo -e "${YELLOW}⏳ Healthcheck: starting (en cours)${NC}"
elif [ -z "$health_status" ]; then
    echo -e "${YELLOW}ℹ️  Pas de healthcheck configuré${NC}"
else
    print_result 1 "Healthcheck: $health_status"
fi
echo ""

# 6. Test des endpoints
echo -e "${YELLOW}[6/8] Test des endpoints API…${NC}"
echo ""

test_endpoint "/" "GET / (root)"
test_endpoint "/health" "GET /health"
test_endpoint "/status" "GET /status"

# 7. Afficher les logs récents
echo -e "${YELLOW}[7/8] Logs récents du container…${NC}"
echo "─────────────────────────────────────"
docker logs "$CONTAINER_NAME" --tail 20
echo "─────────────────────────────────────"
echo ""

# 8. Résumé
echo -e "${YELLOW}[8/8] Résumé des services…${NC}"
docker ps --filter "network=Homebox" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "======================================"
echo "   ✅ Tests terminés"
echo "======================================"
echo ""
echo "📝 Commandes utiles:"
echo "   - Voir les logs:     docker logs $CONTAINER_NAME -f"
echo "   - Redémarrer:        docker restart $CONTAINER_NAME"
echo "   - Entrer dans le container: docker exec -it $CONTAINER_NAME bash"
echo "   - API docs:          http://localhost:4000/docs"
echo ""
