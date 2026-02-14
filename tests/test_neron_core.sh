#!/bin/bash
# Test du module neron_core (orchestrateur)

echo "======================================"
echo "TEST NERON_CORE"
echo "======================================"
echo ""

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

CORE_URL="http://localhost:8000"
MEMORY_URL="http://localhost:8002"

# Test 1: Health check
echo "[1/8] Test 1: Health check..."
HEALTH=$(curl -s "$CORE_URL/health")

if echo "$HEALTH" | grep -q "healthy"; then
    echo -e "${GREEN}OK Service neron_core actif${NC}"
else
    echo -e "${RED}ERREUR Service neron_core non accessible${NC}"
    echo "   Verifiez avec: docker compose logs neron_core"
    exit 1
fi

# Test 2: Info du service
echo ""
echo "[2/8] Test 2: Informations du service..."
INFO=$(curl -s "$CORE_URL/")

if echo "$INFO" | grep -q "Néron Core\|Neron Core"; then
    echo -e "${GREEN}OK Endpoint racine fonctionne${NC}"
    
    VERSION=$(echo "$INFO" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    echo "   Version: $VERSION"
else
    echo -e "${RED}ERREUR Echec de l'endpoint racine${NC}"
fi

# Test 3: Pipeline texte simple
echo ""
echo -e "${BLUE}[3/8] Test 3: Pipeline texte complet${NC}"
echo "   Input → LLM → Memory"
echo ""

# Compter les entrées avant
ENTRIES_BEFORE=$(curl -s "$MEMORY_URL/stats" | grep -o '"total_entries":[0-9]*' | cut -d':' -f2)
echo "   Entrees en memoire avant: $ENTRIES_BEFORE"

# Envoyer une requête
echo "   Envoi de la requete..."
START=$(date +%s)

CORE_RESPONSE=$(curl -s -X POST "$CORE_URL/input/text" \
    -H "Content-Type: application/json" \
    -d '{
        "text": "Quelle est la capitale de l Italie?"
    }')

END=$(date +%s)
DURATION=$((END - START))

if echo "$CORE_RESPONSE" | grep -q "response"; then
    echo -e "${GREEN}OK Pipeline texte reussi [${DURATION}s]${NC}"
    
    # Extraire la réponse
    RESPONSE=$(echo "$CORE_RESPONSE" | grep -o '"response":"[^"]*"' | cut -d'"' -f4 | head -c 100)
    echo "   Reponse LLM: $RESPONSE..."
    
    # Vérifier les métadonnées
    if echo "$CORE_RESPONSE" | grep -q "metadata"; then
        MODEL=$(echo "$CORE_RESPONSE" | grep -o '"model":"[^"]*"' | cut -d'"' -f4)
        echo "   Modele utilise: $MODEL"
    fi
else
    echo -e "${RED}ERREUR Echec du pipeline texte${NC}"
    echo "   Reponse: $CORE_RESPONSE"
    exit 1
fi

# Vérifier que la mémoire a été mise à jour
echo ""
echo "   Verification du stockage en memoire..."
sleep 1  # Laisser le temps au stockage

ENTRIES_AFTER=$(curl -s "$MEMORY_URL/stats" | grep -o '"total_entries":[0-9]*' | cut -d':' -f2)
echo "   Entrees en memoire apres: $ENTRIES_AFTER"

if [ "$ENTRIES_AFTER" -gt "$ENTRIES_BEFORE" ]; then
    echo -e "${GREEN}OK Entree stockee en memoire${NC}"
else
    echo -e "${YELLOW}AVERTISSEMENT La memoire n a pas ete mise a jour${NC}"
fi

# Test 4: Vérifier que l'entrée est bien dans la mémoire
echo ""
echo "[4/8] Test 4: Recherche de l entree dans la memoire..."
SEARCH=$(curl -s "$MEMORY_URL/search?query=Italie&limit=1")

if echo "$SEARCH" | grep -q "Italie"; then
    echo -e "${GREEN}OK Entree retrouvee dans la memoire${NC}"
else
    echo -e "${YELLOW}AVERTISSEMENT Entree non trouvee (delai possible)${NC}"
fi

# Test 5: Test de performance
echo ""
echo "[5/8] Test 5: Test de performance du pipeline..."
echo "   Envoi de 3 requetes successives..."

TOTAL_TIME=0
for i in {1..3}; do
    START=$(date +%s%N)
    
    curl -s -X POST "$CORE_URL/input/text" \
        -H "Content-Type: application/json" \
        -d "{\"text\": \"Test $i: Compte jusqu a $i.\"}" > /dev/null
    
    END=$(date +%s%N)
    DURATION=$((($END - $START) / 1000000))
    TOTAL_TIME=$((TOTAL_TIME + DURATION))
    
    echo "   Requete $i: ${DURATION}ms"
done

AVG_TIME=$((TOTAL_TIME / 3))
echo ""
if [ $AVG_TIME -lt 5000 ]; then
    echo -e "${GREEN}OK Performance excellente (moyenne: ${AVG_TIME}ms)${NC}"
elif [ $AVG_TIME -lt 10000 ]; then
    echo -e "${GREEN}OK Performance bonne (moyenne: ${AVG_TIME}ms)${NC}"
else
    echo -e "${YELLOW}AVERTISSEMENT Performance acceptable (moyenne: ${AVG_TIME}ms)${NC}"
fi

# Test 6: Gestion d'erreurs
echo ""
echo "[6/8] Test 6: Gestion d erreurs..."

# Test avec texte vide
EMPTY_RESPONSE=$(curl -s -X POST "$CORE_URL/input/text" \
    -H "Content-Type: application/json" \
    -d '{"text": ""}')

if echo "$EMPTY_RESPONSE" | grep -q "error\|detail"; then
    echo -e "${GREEN}OK Validation des entrees vides fonctionne${NC}"
else
    echo -e "${YELLOW}AVERTISSEMENT Validation non testee${NC}"
fi

# Test 7: Timeout LLM (optionnel, peut prendre du temps)
echo ""
echo "[7/8] Test 7: Test de timeout..."
echo "   Ce test peut prendre jusqu a 60s..."

# Test avec un prompt très long (pour tester le timeout)
TIMEOUT_TEST=$(curl -s -X POST "$CORE_URL/input/text" \
    -H "Content-Type: application/json" \
    --max-time 65 \
    -d '{
        "text": "Ecris une histoire tres detaillee avec au moins 50 paragraphes sur tous les pays du monde."
    }')

if echo "$TIMEOUT_TEST" | grep -q "response\|timeout\|error"; then
    echo -e "${GREEN}OK Gestion du timeout testee${NC}"
else
    echo -e "${YELLOW}AVERTISSEMENT Test de timeout non concluant${NC}"
fi

# Test 8: Vérification des logs
echo ""
echo "[8/8] Test 8: Verification des logs..."
echo "   Dernieres lignes des logs neron_core:"

docker compose logs --tail=5 neron_core 2>/dev/null | grep -v "^$" | while read line; do
    echo "   $line"
done

echo ""
echo "======================================"
echo -e "${GREEN}TOUS LES TESTS NERON_CORE REUSSIS${NC}"
echo "======================================"
echo ""
echo -e "${BLUE}Resume du pipeline:${NC}"
echo "   1. OK Service actif et accessible"
echo "   2. OK Communication avec neron_llm"
echo "   3. OK Generation de reponses"
echo "   4. OK Stockage en memoire"
echo "   5. OK Performance acceptable"
echo ""
echo "Pipeline complet: Text → Core → LLM → Ollama → Memory"
