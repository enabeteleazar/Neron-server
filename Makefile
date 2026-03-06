# ============================================
#  Néron AI v2.0 — Makefile
# ============================================

BASE_DIR  := /mnt/usb-storage/Neron_AI
VENV      := $(BASE_DIR)/venv
PYTHON    := $(VENV)/bin/python3
PIP       := $(VENV)/bin/pip
SERVICE   := neron
LOG_DIR   := $(BASE_DIR)/logs

.PHONY: install start stop restart status logs update help clean

# --- Défaut ---
all: help

help:
	@echo ""
	@echo "  🧠 Néron AI v2.0 — Commandes disponibles"
	@echo ""
	@echo "  make install    — installer Néron (deps, venv, systemd)"
	@echo "  make start      — démarrer le service"
	@echo "  make stop       — arrêter le service"
	@echo "  make restart    — redémarrer le service"
	@echo "  make status     — état du service"
	@echo "  make logs       — logs en direct"
	@echo "  make update     — git pull + restart"
	@echo "  make clean      — nettoyer venv et logs"
	@echo ""

install:
	@echo "🔧 Installation de Néron AI..."
	@echo ""
	@# Dépendances système
	@echo "📦 Installation des dépendances système..."
	@sudo apt-get update -qq
	@sudo apt-get install -y -qq \
		python3.12-venv \
		python3-pip \
		espeak \
		libespeak1 \
		ffmpeg \
		git \
		curl \
		tree \
		nano \
		make
	@echo "✔ Dépendances système OK"
	@# Venv
	@echo "🐍 Création du venv Python..."
	@test -d $(VENV) || python3 -m venv $(VENV)
	@$(PIP) install --upgrade pip -q
	@$(PIP) install -r $(BASE_DIR)/requirements.txt -q
	@echo "✔ Venv OK"
	@# Logs
	@mkdir -p $(LOG_DIR)
	@echo "✔ Dossier logs OK"
	@# .env
	@test -f $(BASE_DIR)/.env || cp $(BASE_DIR)/.env.example $(BASE_DIR)/.env
	@echo "✔ .env OK"
	@# Systemd
	@echo "⚙️  Configuration systemd..."
	@sudo cp $(BASE_DIR)/neron.service /etc/systemd/system/
	@sudo systemctl daemon-reload
	@sudo systemctl enable $(SERVICE)
	@echo "✔ Service systemd activé"
	@echo ""
	@echo "✅ Installation terminée !"
	@echo ""
	@echo "  👉 Éditez votre .env : nano $(BASE_DIR)/.env"
	@echo "  👉 Puis lancez      : make start"
	@echo ""

start:
	@echo "▶  Démarrage de Néron..."
	@sudo systemctl start $(SERVICE)
	@sleep 2
	@sudo systemctl is-active --quiet $(SERVICE) && \
		echo "✔ Néron démarré" || \
		(echo "❌ Échec — make logs pour plus d'infos" && exit 1)

stop:
	@echo "⏹  Arrêt de Néron..."
	@sudo systemctl stop $(SERVICE)
	@echo "✔ Néron arrêté"

restart:
	@echo "🔄 Redémarrage de Néron..."
	@sudo systemctl restart $(SERVICE)
	@sleep 2
	@sudo systemctl is-active --quiet $(SERVICE) && \
		echo "✔ Néron redémarré" || \
		(echo "❌ Échec — make logs pour plus d'infos" && exit 1)

status:
	@sudo systemctl status $(SERVICE) --no-pager

logs:
	@sudo journalctl -u $(SERVICE) -f

update:
	@echo "🔄 Mise à jour de Néron..."
	@git -C $(BASE_DIR) pull origin main
	@$(PIP) install -r $(BASE_DIR)/requirements.txt -q
	@sudo systemctl restart $(SERVICE)
	@sleep 2
	@sudo systemctl is-active --quiet $(SERVICE) && \
		echo "✔ Néron mis à jour et redémarré" || \
		echo "❌ Échec au redémarrage"

clean:
	@echo "🧹 Nettoyage..."
	@read -p "Supprimer le venv et les logs ? [o/N] " confirm && \
		[ "$$confirm" = "o" ] || exit 0
	@rm -rf $(VENV)
	@rm -f $(LOG_DIR)/*.log
	@echo "✔ Nettoyage terminé"

