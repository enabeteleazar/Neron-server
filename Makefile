# ============================================
#  Néron AI v2.0 — Makefile
# ============================================

BASE_DIR  := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
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
	@echo "[Installation / Maintenance]"
	@echo "  $(BOLD)make install$(RESET)    -- installer Neron"
	@echo "  $(BOLD)make update$(RESET)     -- git pull + restart"
	@echo "  $(BOLD)make clean$(RESET)      -- nettoyer venv et logs"
	@echo "  $(BOLD)make version$(RESET)    -- versions Neron / Python / Ollama"
	@echo ""
	@echo "[Services]"
	@echo "  $(BOLD)make start$(RESET)      -- demarrer le service"
	@echo "  $(BOLD)make stop$(RESET)       -- arreter le service"
	@echo "  $(BOLD)make restart$(RESET)    -- redemarrer le service"
	@echo "  $(BOLD)make status$(RESET)     -- etat du service"
	@echo "  $(BOLD)make logs$(RESET)       -- logs en direct"
	@echo ""
	@echo "[Sauvegarde]"
	@echo "  $(BOLD)make backup$(RESET)     -- sauvegarder DB + neron.yaml"
	@echo "  $(BOLD)make restore$(RESET)    -- restaurer une sauvegarde"
	@echo ""
	@echo "[Diagnostic]"
	@echo "  $(BOLD)make test$(RESET)       -- tester l'API et Ollama"
	@echo "  $(BOLD)make env$(RESET)        -- afficher la config active"
	@echo ""
	@echo "[Integration]"
	@echo "  $(BOLD)make ollama$(RESET)     -- gerer le modele Ollama"
	@echo "  $(BOLD)make telegram$(RESET)   -- configurer les bots Telegram"
	@echo "  $(BOLD)make ha-agent$(RESET)   -- configurer les homeAssistant"

install:
	@echo "🔧 Installation de Néron AI..."
	@echo ""
	@# Dépendances système
	@echo "📦 Installation des dépendances système..."
	@sudo apt-get update -qq
	@sudo apt-get install -y -qq \
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
	@sed -e "s|__NERON_DIR__|$(BASE_DIR)|g" \
		-e "s|__NERON_USER__|$(shell whoami)|g" \
		$(BASE_DIR)/neron.service > /tmp/neron.service
	@sudo cp /tmp/neron.service /etc/systemd/system/neron.service
	@rm /tmp/neron.service
	@sudo systemctl daemon-reload
	@sudo systemctl enable $(SERVICE)
	@echo "✔ Service systemd activé"
	@echo ""
	@echo "✅ Installation terminée !"
	@echo ""
	@echo "🦙 Démarrage Ollama..."
	@ollama serve > /dev/null 2>&1 & sleep 3
	@echo "📥 Téléchargement du modèle par défaut..."
	@MODEL=$$(grep OLLAMA_MODEL $(BASE_DIR)/.env | cut -d= -f2 | tr -d " ") && \
		[ -n "$$MODEL" ] && ollama pull $$MODEL || ollama pull llama3.2:3b
	@echo "✔ Modèle prêt"
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
	@git -C $(BASE_DIR) pull origin master
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


backup:
	@echo "💾 Sauvegarde de Néron..."
	@BACKUP_DIR=$(BASE_DIR)/backups/$$(date +%Y%m%d_%H%M%S) && \
		mkdir -p $$BACKUP_DIR && \
		cp $(BASE_DIR)/.env $$BACKUP_DIR/.env && \
		cp $(BASE_DIR)/data/memory.db $$BACKUP_DIR/memory.db 2>/dev/null || true && \
		echo "✔ Sauvegarde créée : $$BACKUP_DIR"

restore:
	@echo "📂 Sauvegardes disponibles :"
	@ls -lt $(BASE_DIR)/backups/ 2>/dev/null | grep "^d" | awk '{print NR". "$$NF}' || echo "  Aucune sauvegarde trouvée"
	@echo ""
	@read -p "Nom du dossier à restaurer : " BACKUP && \
		test -d $(BASE_DIR)/backups/$$BACKUP || (echo "❌ Introuvable" && exit 1) && \
		cp $(BASE_DIR)/backups/$$BACKUP/.env $(BASE_DIR)/.env && \
		cp $(BASE_DIR)/backups/$$BACKUP/memory.db $(BASE_DIR)/data/memory.db 2>/dev/null || true && \
		echo "✔ Restauration terminée — make restart pour appliquer"

test:
	@echo "🧪 Test de l'API Néron..."
	@curl -sf http://localhost:$(shell grep NERON_CORE_HTTP $(BASE_DIR)/.env | cut -d= -f2)/health > /dev/null && \
		echo "✔ Core API répond" || echo "❌ Core API ne répond pas"
	@curl -sf http://localhost:11434/api/tags > /dev/null && \
		echo "✔ Ollama répond" || echo "❌ Ollama ne répond pas"

env:
	@echo ""
	@echo "  ⚙️  Configuration active (tokens masqués)"
	@echo ""
	@echo ""
	@grep -E "^(OLLAMA|NERON_CORE_HTTP|WHISPER|STT_|LOG_|WATCHDOG_|CONTEXT_|TZ|OLLAMA_MODEL)" $(BASE_DIR)/.env | \
		grep -v "TOKEN\|token" | sed 's/^/  /'
	@echo ""

version:
	@echo ""
	@echo "  🧠 Néron AI"
	@grep -m1 "^VERSION" $(BASE_DIR)/modules/neron_core/app.py 2>/dev/null | \
		cut -d'"' -f2 | awk '{print "  Version  : "$$1}' || echo "  Version  : inconnue"
	@echo "  Python   : $$(python3 --version 2>&1 | cut -d' ' -f2)"
	@echo "  Ollama   : $$(ollama --version 2>/dev/null || echo 'non trouvé')"
	@echo "  Modèle   : $$(grep OLLAMA_MODEL $(BASE_DIR)/.env | cut -d= -f2)"
	@echo "  Service  : $$(systemctl is-active neron 2>/dev/null || echo 'inactif')"
	@echo ""

ollama:
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  🦙 Gestion du modèle Ollama"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "  Modèles installés :"
	@ollama list 2>/dev/null | tail -n +2 | awk '{print "  • "$$1}' || echo "  aucun"
	@echo ""
	@echo "  Modèles recommandés :"
	@echo "  • llama3.2:1b   — léger      (~1GB)"
	@echo "  • llama3.2:3b   — équilibré  (~2GB)"
	@echo "  • mistral       — performant (~4GB)"
	@echo "  • gemma3        — Google     (~5GB)"
	@echo "  • phi3          — Microsoft  (~2GB)"
	@echo ""
	@CURRENT=$$(grep OLLAMA_MODEL $(BASE_DIR)/.env | cut -d= -f2) && \
		echo "  Modèle actuel : $$CURRENT" && \
		echo "" && \
		read -p "  Entrée = garder $$CURRENT, ou tapez un nouveau modèle : " MODEL && \
		MODEL=$${MODEL:-$$CURRENT} && \
		echo "" && \
		echo "📥 Téléchargement de $$MODEL..." && \
		if ollama pull $$MODEL; then \
			echo "" && \
			echo "✔ Téléchargement réussi" && \
			sed -i "s/^OLLAMA_MODEL=.*/OLLAMA_MODEL=$$MODEL/" $(BASE_DIR)/.env && \
			echo "✔ .env mis à jour : OLLAMA_MODEL=$$MODEL" && \
			echo "" && \
			read -p "  Redémarrer Néron maintenant ? [O/n] " RESTART && \
			[ "$$RESTART" != "n" ] && $(MAKE) -C $(BASE_DIR) restart || echo "  👉 make restart quand vous êtes prêt"; \
		else \
			echo "" && \
			echo "❌ Échec du téléchargement — .env non modifié" && \
			echo "  Modèle actif inchangé : $$CURRENT"; \
		fi

telegram:
	@bash $(BASE_DIR)/install.sh --telegram-only

