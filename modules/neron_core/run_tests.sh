#!/bin/bash

# run_tests.sh - Neron Core v1.3.1

# A placer dans : modules/neron_core/

# Usage : bash run_tests.sh [–coverage]

NERON_CORE_DIR=”$(cd “$(dirname “$0”)” && pwd)”
VENV_DIR=”$NERON_CORE_DIR/.venv”

echo “=================================”
echo “  Neron Core - Tests v1.3.1”
echo “=================================”
echo “”

# Verification Python

if ! command -v python3 &>/dev/null; then
echo “ERREUR : Python3 introuvable”
exit 1
fi
echo “OK Python3 : $(python3 –version)”

# Creation venv si absent

if [ ! -d “$VENV_DIR” ]; then
echo “Creation de l environnement virtuel…”
python3 -m venv “$VENV_DIR”
fi

# Activation venv

source “$VENV_DIR/bin/activate”
echo “OK Venv active”

# Installation des dependances

echo “Installation des dependances…”
pip install –quiet pytest pytest-asyncio httpx fastapi pydantic
echo “OK Dependances installees”
echo “”

# Se placer dans neron_core

cd “$NERON_CORE_DIR”

# Options

COVERAGE=false
for arg in “$@”; do
case $arg in
–coverage|-c) COVERAGE=true ;;
esac
done

# Lancement pytest

if [ “$COVERAGE” = true ]; then
pip install –quiet pytest-cov
echo “Lancement avec coverage…”
pytest tests/ -v –cov=. –cov-report=term-missing –cov-omit=“tests/*”
else
echo “Lancement des tests…”
pytest tests/ -v
fi

STATUS=$?

echo “”
if [ $STATUS -eq 0 ]; then
echo “=================================”
echo “  SUCCES : tous les tests passes”
echo “=================================”
else
echo “=================================”
echo “  ECHEC : des tests ont echoue”
echo “=================================”
fi

exit $STATUS
