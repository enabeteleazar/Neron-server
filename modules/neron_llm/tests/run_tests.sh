#!/bin/bash
# modules/neron_llm/run_tests.sh

"""
Script pour lancer les tests du module Néron LLM
Usage: ./run_tests.sh [options]
"""

set -e

# Couleurs pour l'output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==================================${NC}"
echo -e "${BLUE}  Tests Néron LLM${NC}"
echo -e "${BLUE}==================================${NC}"
echo ""

# Fonction d'aide
show_help() {
    echo "Usage: ./run_tests.sh [options]"
    echo ""
    echo "Options:"
    echo "  -h, --help          Afficher cette aide"
    echo "  -u, --unit          Lancer uniquement les tests unitaires"
    echo "  -i, --integration   Lancer uniquement les tests d'intégration"
    echo "  -c, --coverage      Générer un rapport de coverage"
    echo "  -v, --verbose       Mode verbose"
    echo "  -f, --fast          Mode rapide (sans coverage)"
    echo "  --install           Installer les dépendances d'abord"
    echo ""
    echo "Exemples:"
    echo "  ./run_tests.sh                    # Tous les tests"
    echo "  ./run_tests.sh -u -c              # Tests unitaires avec coverage"
    echo "  ./run_tests.sh -v                 # Mode verbose"
    echo "  ./run_tests.sh --install -c       # Installer puis tester avec coverage"
}

# Variables
INSTALL=false
UNIT_ONLY=false
INTEGRATION_ONLY=false
COVERAGE=false
VERBOSE=""
FAST=false

# Parser les arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -u|--unit)
            UNIT_ONLY=true
            shift
            ;;
        -i|--integration)
            INTEGRATION_ONLY=true
            shift
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE="-vv"
            shift
            ;;
        -f|--fast)
            FAST=true
            shift
            ;;
        --install)
            INSTALL=true
            shift
            ;;
        *)
            echo -e "${RED}Option inconnue: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Installer les dépendances si demandé
if [ "$INSTALL" = true ]; then
    echo -e "${YELLOW}📦 Installation des dépendances...${NC}"
    pip install -r requirements.txt
    echo -e "${GREEN}✓ Dépendances installées${NC}"
    echo ""
fi

# Vérifier que pytest est installé
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}❌ pytest n'est pas installé${NC}"
    echo -e "${YELLOW}Installez-le avec: pip install -r requirements.txt${NC}"
    exit 1
fi

# Construire la commande pytest
PYTEST_CMD="pytest"

# Ajouter les options
if [ "$VERBOSE" != "" ]; then
    PYTEST_CMD="$PYTEST_CMD $VERBOSE"
fi

# Sélection des tests
if [ "$UNIT_ONLY" = true ]; then
    echo -e "${BLUE}🧪 Lancement des tests unitaires...${NC}"
    PYTEST_CMD="$PYTEST_CMD -m \"not integration\""
elif [ "$INTEGRATION_ONLY" = true ]; then
    echo -e "${BLUE}🔗 Lancement des tests d'intégration...${NC}"
    PYTEST_CMD="$PYTEST_CMD -m integration"
else
    echo -e "${BLUE}🧪 Lancement de tous les tests...${NC}"
fi

# Coverage
if [ "$COVERAGE" = true ] && [ "$FAST" = false ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=. --cov-report=html --cov-report=term-missing"
fi

# Mode rapide
if [ "$FAST" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --tb=short"
fi

echo -e "${YELLOW}Commande: $PYTEST_CMD${NC}"
echo ""

# Lancer les tests
if eval $PYTEST_CMD; then
    echo ""
    echo -e "${GREEN}==================================${NC}"
    echo -e "${GREEN}  ✓ Tous les tests sont passés !${NC}"
    echo -e "${GREEN}==================================${NC}"
    
    if [ "$COVERAGE" = true ]; then
        echo ""
        echo -e "${BLUE}📊 Rapport de coverage disponible dans htmlcov/index.html${NC}"
    fi
    
    exit 0
else
    echo ""
    echo -e "${RED}==================================${NC}"
    echo -e "${RED}  ✗ Certains tests ont échoué${NC}"
    echo -e "${RED}==================================${NC}"
    exit 1
fi
