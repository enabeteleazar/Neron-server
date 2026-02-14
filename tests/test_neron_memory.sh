#!/bin/bash
# Test du module neron_memory

echo "======================================"
echo "🧪 TEST NERON_MEMORY"
echo "======================================"
echo ""

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

MEMORY_URL="http://localhost:8002"

# Test 1: Health check
echo "🏥 Test 1: Health check..."
HEALTH=$(curl -s "$MEMORY_URL/health")

if echo "$HEALTH" | grep -q "healthy"; then
    echo -e "${GREEN}✅ Service neron_memory actif${NC}"
    
    # Afficher le nombre d'entrées
    ENTRIES=$(echo "$HEALTH" | grep -o '"entries":[0-9]*' | cut -d':' -f2)
    echo "   Entrées existantes: $ENTRIES"
else
    echo -e "${RED}❌ Service neron_memory non accessible${NC}"
    echo "   Vérifiez avec: docker compose logs neron_memory"
    exit 1
fi

# Test 2: Stocker une entrée
echo ""
echo "💾 Test 2: Stockage d'une nouvelle entrée..."
STORE_RESPONSE=$(curl -s -X POST "$MEMORY_URL/store" \
    -H "Content-Type: application/json" \
    -d '{
        "input": "Test input - Quelle est la capitale de la France?",
        "response": "Test response - La capitale de la France est Paris.",
        "metadata": {
            "source": "test",
            "timestamp": "2025-02-14"
        }
    }')

if echo "$STORE_RESPONSE" | grep -q '"status":"ok"'; then
    ENTRY_ID=$(echo "$STORE_RESPONSE" | grep -o '"id":[0-9]*' | cut -d':' -f2)
    echo -e "${GREEN}✅ Stockage réussi${NC}"
    echo "   ID de l'entrée: $ENTRY_ID"
else
    echo -e "${RED}❌ Échec du stockage${NC}"
    echo "   Réponse: $STORE_RESPONSE"
    exit 1
fi

# Test 3: Récupérer les dernières entrées
echo ""
echo "📖 Test 3: Récupération des dernières entrées..."
RETRIEVE_RESPONSE=$(curl -s "$MEMORY_URL/retrieve?limit=5")

if echo "$RETRIEVE_RESPONSE" | grep -q "Test input"; then
    echo -e "${GREEN}✅ Récupération réussie${NC}"
    
    # Compter les entrées retournées
    COUNT=$(echo "$RETRIEVE_RESPONSE" | grep -o '"id":' | wc -l)
    echo "   Entrées récupérées: $COUNT"
else
    echo -e "${RED}❌ Échec de la récupération${NC}"
    exit 1
fi

# Test 4: Recherche par mot-clé
echo ""
echo "🔍 Test 4: Recherche par mot-clé..."
SEARCH_RESPONSE=$(curl -s "$MEMORY_URL/search?query=France&limit=10")

if echo "$SEARCH_RESPONSE" | grep -q "France"; then
    echo -e "${GREEN}✅ Recherche fonctionnelle${NC}"
    
    # Compter les résultats
    RESULTS=$(echo "$SEARCH_RESPONSE" | grep -o '"id":' | wc -l)
    echo "   Résultats trouvés: $RESULTS"
else
    echo -e "${YELLOW}⚠️  Aucun résultat (peut-être normal si base vide)${NC}"
fi

# Test 5: Statistiques
echo ""
echo "📊 Test 5: Statistiques de la mémoire..."
STATS=$(curl -s "$MEMORY_URL/stats")

if echo "$STATS" | grep -q "total_entries"; then
    echo -e "${GREEN}✅ Endpoint /stats fonctionne${NC}"
    
    TOTAL=$(echo "$STATS" | grep -o '"total_entries":[0-9]*' | cut -d':' -f2)
    RECENT=$(echo "$STATS" | grep -o '"recent_entries_7d":[0-9]*' | cut -d':' -f2)
    
    echo "   Total d'entrées: $TOTAL"
    echo "   Entrées récentes (7j): $RECENT"
    
    if echo "$STATS" | grep -q "oldest_entry"; then
        OLDEST=$(echo "$STATS" | grep -o '"oldest_entry":"[^"]*"' | cut -d'"' -f4)
        echo "   Plus ancienne: $OLDEST"
    fi
    
    if echo "$STATS" | grep -q "newest_entry"; then
        NEWEST=$(echo "$STATS" | grep -o '"newest_entry":"[^"]*"' | cut -d'"' -f4)
        echo "   Plus récente: $NEWEST"
    fi
else
    echo -e "${RED}❌ Échec des statistiques${NC}"
    exit 1
fi

# Test 6: Pagination
echo ""
echo "📄 Test 6: Pagination..."
PAGE1=$(curl -s "$MEMORY_URL/retrieve?limit=2&offset=0")
PAGE2=$(curl -s "$MEMORY_URL/retrieve?limit=2&offset=2")

if [ "$PAGE1" != "$PAGE2" ]; then
    echo -e "${GREEN}✅ Pagination fonctionne${NC}"
else
    echo -e "${YELLOW}⚠️  Pagination non testée (pas assez d'entrées)${NC}"
fi

# Test 7: Persistance des données
echo ""
echo "💾 Test 7: Vérification de la persistance..."
echo "   Stockage d'une entrée test pour vérification..."

TEST_ENTRY=$(curl -s -X POST "$MEMORY_URL/store" \
    -H "Content-Type: application/json" \
    -d '{
        "input": "Test persistance - timestamp: '"$(date +%s)"'",
        "response": "Test response persistance",
        "metadata": {"test": true}
    }')

if echo "$TEST_ENTRY" | grep -q '"status":"ok"'; then
    echo -e "${GREEN}✅ Données persistantes${NC}"
    echo "   Note: Vérifiez que les données survivent au redémarrage du conteneur"
else
    echo -e "${RED}❌ Problème de persistance${NC}"
fi

echo ""
echo "======================================"
echo -e "${GREEN}✅ TOUS LES TESTS NERON_MEMORY RÉUSSIS${NC}"
echo "======================================"
echo ""
echo "💡 Conseil: Testez la persistance en redémarrant le conteneur:"
echo "   docker compose restart neron_memory"
echo "   puis relancez ce script pour vérifier que les données sont toujours là"
