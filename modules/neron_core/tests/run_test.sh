#!/bin/bash
# run_tests.sh — Néron Core v1.3.1

# Lance les tests pytest depuis le dossier neron_core

set -euo pipefail

# — Couleurs —

GREEN=’\033[0;32m’
RED=’\033[0;31m’
YELLOW=’\033[1;33m’
BLUE=’\033[0;34m’
NC=’\033[0m’

# — Config —

NERON_CORE_DIR=”$(cd “$(dirname “$0”)” && pwd)”
VENV_DIR=”$NERON_CORE_DIR/.venv”

echo -e “${BLUE}=================================${NC}”
echo -e “${BLUE}  Néron Core — Tests v1.3.1      ${NC}”
echo -e “${BLUE}=================================${NC}”
echo “”

# — Vérification Python —

if ! command -v python3 &>/dev/null; then
echo -e “${RED}❌ Python3 introuvable${NC}”
exit 1
fi
echo -e “${GREEN}✅ Python3 : $(python3 –version)${NC}”

# — Création venv si absent —

if [ ! -d “$VENV_DIR” ]; then
echo -e “${YELLOW}📦 Création de l’environnement virtuel…${NC}”
python3 -m venv “$VENV_DIR”
fi

# — Activation venv —

source “$VENV_DIR/bin/activate”
echo -e “${GREEN}✅ Venv activé : $VENV_DIR${NC}”

# — Installation des dépendances —

echo -e “${YELLOW}📦 Installation des dépendances de test…${NC}”
pip install –quiet pytest pytest-asyncio httpx fastapi pydantic

echo -e “${GREEN}✅ Dépendances installées${NC}”
echo “”

# — Lancement des tests —

cd “$NERON_CORE_DIR”

# Parser les arguments

COVERAGE=false
VERBOSE=false

for arg in “$@”; do
case $arg in
–coverage|-c) COVERAGE=true ;;
–verbose|-v)  VERBOSE=true ;;
–help|-h)
echo “Usage: ./run_tests.sh [options]”
echo “  –coverage, -c   Rapport de couverture”
echo “  –verbose, -v    Mode verbose”
exit 0
;;
esac
done

# Construction de la commande pytest

PYTEST_CMD=“pytest tests/”

if [ “$VERBOSE” = true ]; then
PYTEST_CMD=”$PYTEST_CMD -v”
else
PYTEST_CMD=”$PYTEST_CMD -v”   # verbose par défaut pour voir chaque test
fi

if [ “$COVERAGE” = true ]; then
pip install –quiet pytest-cov
PYTEST_CMD=”$PYTEST_CMD –cov=. –cov-report=term-missing –cov-omit=tests/*,*/**pycache**/*”
fi

echo -e “${BLUE}🧪 Lancement : $PYTEST_CMD${NC}”
echo “”

# — Exécution —

if eval “$PYTEST_CMD”; then
echo “”
echo -e “${GREEN}=================================${NC}”
echo -e “${GREEN}  ✅ Tous les tests sont passés !${NC}”
echo -e “${GREEN}=================================${NC}”
exit 0
else
echo “”
echo -e “${RED}=================================${NC}”
echo -e “${RED}  ❌ Des tests ont échoué        ${NC}”
echo -e “${RED}=================================${NC}”
exit 1
fi
