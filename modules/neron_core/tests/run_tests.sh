#!/bin/bash
# modules/neron_core/tests/run_tests.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}   Tests Néron Core             ${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

COVERAGE=false
VERBOSE=""
INSTALL=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--coverage)  COVERAGE=true; shift ;;
        -v|--verbose)   VERBOSE="-vv"; shift ;;
        --install)      INSTALL=true; shift ;;
        -h|--help)
            echo "Usage: ./run_tests.sh [-c] [-v] [--install]"
            echo "  -c  Générer le rapport de coverage"
            echo "  -v  Mode verbose"
            echo "  --install  Installer les dépendances d'abord"
            exit 0
            ;;
        *) echo -e "${RED}Option inconnue: $1${NC}"; exit 1 ;;
    esac
done

if [ "$INSTALL" = true ]; then
    echo -e "${YELLOW}📦 Installation des dépendances...${NC}"
    pip install fastapi uvicorn httpx pydantic pytest pytest-asyncio pytest-cov
    echo -e "${GREEN}✓ OK${NC}"
    echo ""
fi

CMD="pytest tests/ $VERBOSE"

if [ "$COVERAGE" = true ]; then
    CMD="$CMD --cov=. --cov-report=html --cov-report=term-missing"
fi

echo -e "${YELLOW}Commande: $CMD${NC}"
echo ""

if eval $CMD; then
    echo ""
    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN}   ✓ Tous les tests passés !    ${NC}"
    echo -e "${GREEN}================================${NC}"
    [ "$COVERAGE" = true ] && echo -e "${BLUE}📊 Rapport: htmlcov/index.html${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}================================${NC}"
    echo -e "${RED}   ✗ Des tests ont échoué       ${NC}"
    echo -e "${RED}================================${NC}"
    exit 1
fi
