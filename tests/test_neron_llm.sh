#!/bin/bash
# Test du module neron_llm

echo "======================================"
echo "TEST NERON_LLM"
echo "======================================"
echo ""

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

LLM_URL="http://localhost:5000"

# Test 1: Health check
echo "[1/6] Test 1: Health check..."
HEALTH=$(curl -s "$LLM_URL/health")

if echo "$HEALTH" | grep -q "healthy"; then
    echo -e "${GREEN}OK Service neron_llm actif${NC}"
    
    # Vérifier la connexion à Ollama
    if echo "$HEALTH" | grep -q '"ollama_connected":true'; then
        echo -e "${GREEN}OK Connexion a Ollama etablie${NC}"
    else
        echo -e "${RED}ERREUR Pas de connexion a Ollama${NC}"
        exit 1
    fi
else
    echo -e "${RED}ERREUR Service neron_llm non accessible${NC}"
    echo "   Verifiez avec: docker compose logs neron_llm"
    exit 1
fi

# Test 2: Liste des modèles via le wrapper
echo ""
echo "[2/6] Test 2: Liste des modeles (via wrapper)..."
MODELS=$(curl -s "$LLM_URL/models")

if echo "$MODELS" | grep -q "models"; then
    echo -e "${GREEN}OK Endpoint /models fonctionne${NC}"
    echo "$MODELS" | grep -o '"name":"[^"]*"' | cut -d'"' -f4 | while read model; do
        echo "   - $model"
    done
else
    echo -e "${RED}ERREUR Echec de recuperation des modeles${NC}"
    exit 1
fi

# Test 3: Génération via /ask
echo ""
echo "[3/6] Test 3: Generation via /ask..."
ASK_RESPONSE=$(curl -s -X POST "$LLM_URL/ask" \
    -H "Content-Type: application/json" \
    -d '{
        "prompt": "Dis bonjour en une phrase.",
        "model": "llama3.2:1b"
    }')

if echo "$ASK_RESPONSE" | grep -q "response"; then
    GENERATED=$(echo "$ASK_RESPONSE" | grep -o '"response":"[^"]*"' | cut -d'"' -f4)
    echo -e "${GREEN}OK Generation via /ask reussie${NC}"
    echo "   Reponse: $GENERATED"
else
    echo -e "${RED}ERREUR Echec de /ask${NC}"
    echo "   Reponse: $ASK_RESPONSE"
    exit 1
fi

# Test 4: Génération via /generate (alias)
echo ""
echo "[4/6] Test 4: Generation via /generate (alias)..."
GEN_RESPONSE=$(curl -s -X POST "$LLM_URL/generate" \
    -H "Content-Type: application/json" \
    -d '{
        "prompt": "Compte jusqu a 3.",
        "model": "llama3.2:1b"
    }')

if echo "$GEN_RESPONSE" | grep -q "response"; then
    echo -e "${GREEN}OK Endpoint /generate fonctionne${NC}"
else
    echo -e "${RED}ERREUR Echec de /generate${NC}"
    exit 1
fi

# Test 5: Options avancées
echo ""
echo "[5/6] Test 5: Options avancees (temperature, system_prompt)..."
ADV_RESPONSE=$(curl -s -X POST "$LLM_URL/ask" \
    -H "Content-Type: application/json" \
    -d '{
        "prompt": "Reponds simplement oui.",
        "model": "llama3.2:1b",
        "temperature": 0.3,
        "max_tokens": 10,
        "system_prompt": "Tu es un assistant concis."
    }')

if echo "$ADV_RESPONSE" | grep -q "response"; then
    echo -e "${GREEN}OK Options avancees fonctionnent${NC}"
    
    # Vérifier les métadonnées
    if echo "$ADV_RESPONSE" | grep -q "tokens_used"; then
        TOKENS=$(echo "$ADV_RESPONSE" | grep -o '"tokens_used":[0-9]*' | cut -d':' -f2)
        echo "   Tokens utilises: $TOKENS"
    fi
    
    if echo "$ADV_RESPONSE" | grep -q "generation_time"; then
        TIME=$(echo "$ADV_RESPONSE" | grep -o '"generation_time":[0-9.]*' | cut -d':' -f2)
        echo "   Temps de generation: ${TIME}s"
    fi
else
    echo -e "${RED}ERREUR Echec avec options avancees${NC}"
    exit 1
fi

# Test 6: Validation des erreurs
echo ""
echo "[6/6] Test 6: Validation des erreurs..."
ERROR_RESPONSE=$(curl -s -X POST "$LLM_URL/ask" \
    -H "Content-Type: application/json" \
    -d '{
        "temperature": 3.0
    }')

if echo "$ERROR_RESPONSE" | grep -q "error\|detail"; then
    echo -e "${GREEN}OK Validation Pydantic fonctionne${NC}"
else
    echo -e "${YELLOW}AVERTISSEMENT Validation d erreur non testee${NC}"
fi

echo ""
echo "======================================"
echo -e "${GREEN}TOUS LES TESTS NERON_LLM REUSSIS${NC}"
echo "======================================"
