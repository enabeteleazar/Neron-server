#!/bin/bash
# Script master pour tester tous les modules Néron dans l'ordre

set -e

echo "╔════════════════════════════════════════╗"
echo "║  🧪 TESTS COMPLETS NÉRON AI ASSISTANT  ║"
echo "╔════════════════════════════════════════╗"
echo ""

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# Fonction pour afficher un séparateur
separator() {
    echo ""
    echo "----------------------------------------"
    echo ""
}

# Fonction pour vérifier si un conteneur est actif
check_container() {
    local container=$1
    if docker compose ps | grep -q "$container.*Up"; then
        echo -e "${GREEN}✅ $container est actif${NC}"
        return 0
    else
        echo -e "${RED}❌ $container n'est pas actif${NC}"
        return 1
    fi
}

# Vérifier que Docker Compose est accessible
echo "🐳 Vérification de Docker Compose..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker n'est pas installé ou accessible${NC}"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose n'est pas disponible${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker Compose disponible${NC}"

separator

# Vérifier l'état des conteneurs
echo -e "${BOLD}📊 État des conteneurs:${NC}"
echo ""
docker compose ps

separator

echo -e "${BLUE}Vérification des conteneurs requis...${NC}"
REQUIRED_CONTAINERS=("neron_ollama" "neron_llm" "neron_memory" "neron_core")
ALL_UP=true

for container in "${REQUIRED_CONTAINERS[@]}"; do
    if ! check_container "$container"; then
        ALL_UP=false
    fi
done

if [ "$ALL_UP" = false ]; then
    echo ""
    echo -e "${YELLOW}⚠️  Certains conteneurs ne sont pas actifs${NC}"
    echo "   Lancez-les avec: docker compose up -d"
    echo ""
    read -p "Voulez-vous continuer quand même? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

separator

# Rendre les scripts exécutables
chmod +x test_neron_ollama.sh
chmod +x test_neron_llm.sh
chmod +x test_neron_memory.sh
chmod +x test_neron_core.sh

# Variables pour tracker les résultats
declare -A RESULTS

# Fonction pour exécuter un test
run_test() {
    local script=$1
    local name=$2
    
    echo ""
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}▶️  Lancement: $name${NC}"
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    if ./$script; then
        RESULTS[$name]="SUCCESS"
        echo ""
        echo -e "${GREEN}✅ $name: SUCCÈS${NC}"
    else
        RESULTS[$name]="FAILED"
        echo ""
        echo -e "${RED}❌ $name: ÉCHEC${NC}"
        
        read -p "Continuer malgré l'échec? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return 1
        fi
    fi
    
    separator
    sleep 2
}

# ==========================================
# ORDRE DE TEST
# ==========================================

# 1. Test Ollama (base)
run_test "test_neron_ollama.sh" "NERON_OLLAMA" || exit 1

# 2. Test LLM (wrapper)
run_test "test_neron_llm.sh" "NERON_LLM" || exit 1

# 3. Test Memory (stockage)
run_test "test_neron_memory.sh" "NERON_MEMORY" || exit 1

# 4. Test Core (orchestrateur)
run_test "test_neron_core.sh" "NERON_CORE" || exit 1

# ==========================================
# RAPPORT FINAL
# ==========================================

echo ""
echo "╔════════════════════════════════════════╗"
echo "║          📊 RAPPORT FINAL              ║"
echo "╚════════════════════════════════════════╝"
echo ""

TOTAL=0
SUCCESS=0
FAILED=0

for module in "${!RESULTS[@]}"; do
    TOTAL=$((TOTAL + 1))
    
    if [ "${RESULTS[$module]}" = "SUCCESS" ]; then
        SUCCESS=$((SUCCESS + 1))
        echo -e "✅ ${GREEN}$module${NC}: Succès"
    else
        FAILED=$((FAILED + 1))
        echo -e "❌ ${RED}$module${NC}: Échec"
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "Total: $TOTAL | Succès: ${GREEN}$SUCCESS${NC} | Échecs: ${RED}$FAILED${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}${BOLD}🎉 TOUS LES TESTS SONT PASSÉS !${NC}"
    echo ""
    echo "✨ Votre installation Néron AI Assistant est fonctionnelle"
    echo ""
    echo "Prochaines étapes:"
    echo "  • Testez l'interface web: http://localhost:7860"
    echo "  • Consultez les logs: docker compose logs -f"
    echo "  • Essayez différents modèles avec: docker exec -it neron_ollama ollama pull <model>"
    echo ""
    exit 0
else
    echo -e "${RED}${BOLD}⚠️  CERTAINS TESTS ONT ÉCHOUÉ${NC}"
    echo ""
    echo "Actions recommandées:"
    echo "  1. Vérifiez les logs: docker compose logs <service>"
    echo "  2. Redémarrez les services: docker compose restart"
    echo "  3. Vérifiez les variables d'environnement dans .env"
    echo "  4. Assurez-vous qu'un modèle est installé dans Ollama"
    echo ""
    exit 1
fi
