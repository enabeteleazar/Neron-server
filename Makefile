# ============================================
# NÉRON AI — MAKEFILE DEV
# ============================================

.PHONY: help test status submodules clean install-dev

help:
	@echo "NÉRON DEV"
	@echo ""
	@echo "Commandes disponibles :"
	@echo "  make test         Lance les tests"
	@echo "  make status       Affiche l'état Git et des submodules"
	@echo "  make submodules   Initialise/met à jour les submodules"
	@echo "  make clean        Nettoie les caches Python/Pytest"
	@echo "  make install-dev  Installe les dépendances"

test:
	pytest

status:
	git status
	@echo ""
	git submodule status

submodules:
	git submodule update --init --recursive

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -prune -exec rm -rf {} +

install-dev:
	pip install -r requirements/dev.txt 
