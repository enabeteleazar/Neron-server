#!/bin/bash
# Test du module neron_ollama

echo "======================================"
echo "🧪 TEST NERON_OLLAMA"
echo "======================================"
echo ""

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

OLLAMA_URL="http://localhost:11434"

# Test 1: Vérifier que le service répond
echo "📡 Test 1: Vérification du service..."
if curl -s -f "$OLLAMA_URL/api/tags" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Service Ollama actif${NC}"
else
    echo -e "${RED}❌ Service Ollama non accessible${NC}"
    echo "   Vérifiez avec: docker compose ps neron_ollama"
    exit 1
fi

# Test 2: Lister les modèles disponibles
echo ""
echo "📋 Test 2: Liste des modèles installés..."
MODELS=$(curl -s "$OLLAMA_URL/api/tags" | grep -o '"name":"[^"]*"' | cut -d'"' -f4)

if [ -z "$MODELS" ]; then
    echo -e "${YELLOW}⚠️  Aucun modèle installé${NC}"
    echo "   Installez un modèle avec: docker exec -it neron_ollama ollama pull llama3.2:1b"
    exit 1
else
    echo -e "${GREEN}✅ Modèles trouvés:${NC}"
    echo "$MODELS" | while read model; do
        echo "   - $model"
    done
fi

# Test 3: Tester la génération avec un modèle
echo ""
echo "🤖 Test 3: Test de génération..."

# Utiliser le premier modèle disponible
FIRST_MODEL=$(echo "$MODELS" | head -n1)
echo "   Utilisation du modèle: $FIRST_MODEL"

RESPONSE=$(curl -s -X POST "$OLLAMA_URL/api/generate" \
    -H "Content-Type: application/json" \
    -d "{
        \"model\": \"$FIRST_MODEL\",
        \"prompt\": \"Dis bonjour en une phrase.\",
        \"stream\": false
    }")

if echo "$RESPONSE" | grep -q "response"; then
    GENERATED_TEXT=$(echo "$RESPONSE" | grep -o '"response":"[^"]*"' | cut -d'"' -f4)
    echo -e "${GREEN}✅ Génération réussie${NC}"
    echo "   Réponse: $GENERATED_TEXT"
else
    echo -e "${RED}❌ Échec de la génération${NC}"
    echo "   Réponse: $RESPONSE"
    exit 1
fi

# Test 4: Vérifier les performances
echo ""
echo "⏱️  Test 4: Test de performance..."
START=$(date +%s%N)

curl -s -X POST "$OLLAMA_URL/api/generate" \
    -H "Content-Type: application/json" \
    -d "{
        \"model\": \"$FIRST_MODEL\",
        \"prompt\": \"Compte jusqu'à 3.\",
        \"stream\": false
    }" > /dev/null

END=$(date +%s%N)
DURATION=$((($END - $START) / 1000000))

if [ $DURATION -lt 30000 ]; then
    echo -e "${GREEN}✅ Performance OK (${DURATION}ms)${NC}"
else
    echo -e "${YELLOW}⚠️  Performance lente (${DURATION}ms)${NC}"
fi

echo ""
echo "======================================"
echo -e "${GREEN}✅ TOUS LES TESTS OLLAMA RÉUSSIS${NC}"
echo "======================================"
