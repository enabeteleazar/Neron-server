# ============================================
# NÉRON AI — MAKEFILE DEV
# ============================================


.PHONY: help test status submodules clean install-dev install install-check

help:
	@echo "NÉRON DEV"
	@echo ""
	@echo "Commandes disponibles :"
	@echo "  make test         	Lance les tests"
	@echo "  make status       	Affiche l'état Git et des submodules"
	@echo "  make submodules   	Initialise/met à jour les submodules"
	@echo "  make clean        	Nettoie les caches Python/Pytest"
	@echo "  make update		Met a jours les paquets venv"
	@echo "  make install-dev	Installe les dépendances"
	@echo "  make install-check    Compare la config deployee au depot"
	@echo "  make install          Installe la config de deploiement (sudo)"

test:
	pytest

status:
	git status
	@echo ""
	git submodule status

submodules:
	git submodule update --init --recursive

clean:
	@neron clean

update:
	python -m pip install --upgrade pip

ollama:
	curl -fsSL https://ollama.com/install.sh | sh

install-dev:
	pip install -r requirements/dev.txt

install-check:
	@./system/deploy/install.sh check

install:
	sudo ./system/deploy/install.sh install
