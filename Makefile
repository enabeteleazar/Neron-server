#  Néron AI v2.0 — Makefile
# ============================================

BASE_DIR  := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
VENV      := $(BASE_DIR)/venv
PYTHON    := $(VENV)/bin/python3
PIP       := $(VENV)/bin/pip
SERVICE   := neron
LOG_DIR   := $(BASE_DIR)/logs

.PHONY: install start stop restart status logs update help clean ha-agent

# --- Défaut ---
all: help

help:
	@echo ""
	@echo "[Installation / Maintenance]"
	@echo "  make install    -- installer Neron"
	@echo "  make update     -- git pull + restart"
	@echo "  make clean      -- nettoyer venv et logs"
	@echo "  make version    -- versions Neron / Python / Ollama"
	@echo ""
	@echo "[Services]"
	@echo "  make start      -- demarrer le service"
	@echo "  make stop       -- arreter le service"
	@echo "  make restart    -- redemarrer le service"
	@echo "  make status     -- etat du service"
	@echo "  make logs       -- logs en direct"
	@echo ""
	@echo "[Sauvegarde]"
	@echo "  make backup     -- sauvegarder DB + neron.yaml"
	@echo "  make restore    -- restaurer une sauvegarde"
	@echo ""
	@echo "[Diagnostic]"
	@echo "  make test       -- tester l'API et Ollama"
	@echo "  make neron      -- afficher la config active"
	@echo ""
	@echo "[Integration]"
	@echo "  make ollama     -- gerer le modele Ollama"
	@echo "  make telegram   -- configurer les bots Telegram"
	@echo "  make ha-agent   -- configurer Home Assistant"

install:
	@echo "🔧 Installation de Néron AI..."
	@echo ""
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
	@echo "🐍 Création du venv Python..."
	@test -d $(VENV) || python3 -m venv $(VENV)
	@$(PIP) install --upgrade pip -q
	@$(PIP) install -r $(BASE_DIR)/requirements.txt -q
	@echo "✔ Venv OK"
	@mkdir -p $(LOG_DIR)
	@echo "✔ Dossier logs OK"
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
	@echo "  👉 Configurez : nano $(BASE_DIR)/neron.yaml"
	@echo "  👉 Démarrez   : make start"
	@echo ""
	@echo ""
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
		cp $(BASE_DIR)/neron.yaml $$BACKUP_DIR/neron.yaml && \
		cp $(BASE_DIR)/data/memory.db $$BACKUP_DIR/memory.db 2>/dev/null || true && \
		echo "✔ Sauvegarde créée : $$BACKUP_DIR"

restore:
	@echo "📂 Sauvegardes disponibles :"
	@ls -lt $(BASE_DIR)/backups/ 2>/dev/null | grep "^d" | awk '{print NR". "$$NF}' || echo "  Aucune sauvegarde trouvée"
	@echo ""
	@read -p "Nom du dossier à restaurer : " BACKUP && \
		test -d $(BASE_DIR)/backups/$$BACKUP || (echo "❌ Introuvable" && exit 1) && \
		cp $(BASE_DIR)/backups/$$BACKUP/neron.yaml $(BASE_DIR)/neron.yaml && \
		cp $(BASE_DIR)/backups/$$BACKUP/memory.db $(BASE_DIR)/data/memory.db 2>/dev/null || true && \
		echo "✔ Restauration terminée — make restart pour appliquer"

test:
	@echo "🧪 Test de l'API Néron..."
	@curl -sf http://localhost:8010/health > /dev/null && \
		echo "✔ Core API répond" || echo "❌ Core API ne répond pas"
	@curl -sf http://localhost:11434/api/tags > /dev/null && \
		echo "✔ Ollama répond" || echo "❌ Ollama ne répond pas"

neron:
	@echo ""
	@echo "  ⚙️  Configuration active (tokens masqués)"
	@echo ""
	@grep -E "^(OLLAMA|NERON_CORE_HTTP|WHISPER|STT_|LOG_|WATCHDOG_|CONTEXT_|TZ|OLLAMA_MODEL)" $(BASE_DIR)/neron.yaml | \
		grep -v "TOKEN\|token" | sed 's/^/  /'
	@echo ""

version:
	@echo ""
	@echo "  🧠 Néron AI"
	@grep -m1 "^VERSION" $(BASE_DIR)/modules/neron_core/app.py 2>/dev/null | \
		cut -d'"' -f2 | awk '{print "  Version  : "$$1}' || echo "  Version  : inconnue"
	@echo "  Python   : $$(python3 --version 2>&1 | cut -d' ' -f2)"
	@echo "  Ollama   : $$(ollama --version 2>/dev/null || echo 'non trouvé')"
		@echo "  Modèles  :"
	@cat $(BASE_DIR)/neron.yaml | awk '\
		/^[a-zA-Z0-9_]+:/ { \
			agent=$$1; sub(/:$$/,"",agent); next \
		} \
		/^[ \t]+model:/ { \
			model=$$2; gsub(/^[ \t]+|[ \t]+$$/,"",model); \
			if(model!="null" && model!=""){ print "    " agent " : " model } \
		}'
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
	@echo "🔍 Analyse du hardware en cours..."
	@echo ""
	@$(PYTHON) $(BASE_DIR)/scripts/ollama_recommend.py || true
	@echo ""
	@CURRENT=$$($(PYTHON) -c "import yaml; print(yaml.safe_load(open('$(BASE_DIR)/neron.yaml'))['llm']['model'])" 2>/dev/null || echo "llama3.2:3b") && \
		echo "  Modèle actuel : $$CURRENT" && \
		echo "" && \
		read -p "  Entrée = garder $$CURRENT, ou tapez un modèle Ollama : " MODEL && \
		MODEL=$${MODEL:-$$CURRENT} && \
		echo "" && \
		echo "📥 Téléchargement de $$MODEL..." && \
		if ollama pull $$MODEL; then \
			echo "" && \
			echo "✔ Téléchargement réussi" && \
			$(PYTHON) -c "import yaml; f='$(BASE_DIR)/neron.yaml'; d=yaml.safe_load(open(f)); d['llm']['model']='$$MODEL'; yaml.dump(d, open(f,'w'), allow_unicode=True, default_flow_style=False); print('✔ neron.yaml mis à jour : llm.model=$$MODEL')" && \
			echo "" && \
			read -p "  Redémarrer Néron maintenant ? [O/n] " RESTART && \
			[ "$$RESTART" != "n" ] && $(MAKE) -C $(BASE_DIR) restart || echo "  👉 make restart quand vous êtes prêt"; \
		else \
			echo "" && \
			echo "❌ Échec du téléchargement — neron.yaml non modifié" && \
			echo "  Modèle actif inchangé : $$CURRENT"; \
		fi

telegram:
	@bash $(BASE_DIR)/install.sh --telegram-only

ha-agent:
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  🏠 Configuration Home Assistant"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@CURRENT_URL=$$($(PYTHON) -c "import yaml; d=yaml.safe_load(open('$(BASE_DIR)/neron.yaml')); print(d.get('home_assistant',{}).get('url','http://homeassistant.local:8123'))") && \
	CURRENT_ENABLED=$$($(PYTHON) -c "import yaml; d=yaml.safe_load(open('$(BASE_DIR)/neron.yaml')); print(d.get('home_assistant',{}).get('enabled',False))") && \
	echo "  État actuel  : $$CURRENT_ENABLED" && \
	echo "  URL actuelle : $$CURRENT_URL" && \
	echo "" && \
	read -p "  URL Home Assistant [$$CURRENT_URL] : " HA_URL && \
	HA_URL=$${HA_URL:-$$CURRENT_URL} && \
	echo "" && \
	echo "  👉 Générez un token dans HA :" && \
	echo "     Profil → Sécurité → Tokens d'accès longue durée" && \
	echo "" && \
	read -p "  Token (laisser vide pour garder l'actuel) : " HA_TOKEN && \
	if [ -z "$$HA_TOKEN" ]; then \
		HA_TOKEN=$$($(PYTHON) -c "import yaml; d=yaml.safe_load(open('$(BASE_DIR)/neron.yaml')); print(d.get('home_assistant',{}).get('token',''))"); \
	fi && \
	echo "" && \
	echo "🔍 Test de connexion vers $$HA_URL..." && \
	HTTP_CODE=$$(curl -s -o /dev/null -w "%{http_code}" \
		-H "Authorization: Bearer $$HA_TOKEN" \
		$$HA_URL/api/) && \
	if [ "$$HTTP_CODE" = "200" ]; then \
		echo "✔ Connexion réussie (HTTP $$HTTP_CODE)" && \
		$(PYTHON) $(BASE_DIR)/scripts/ha_setup.py "$(BASE_DIR)/neron.yaml" "$$HA_URL" "$$HA_TOKEN" && \
		echo "" && \
		read -p "  Redémarrer Néron maintenant ? [O/n] " RESTART && \
		[ "$$RESTART" != "n" ] && $(MAKE) -C $(BASE_DIR) restart || echo "  👉 make restart quand vous êtes prêt"; \
	else \
		echo "❌ Connexion échouée (HTTP $$HTTP_CODE)" && \
		echo "  Vérifiez l'URL et le token — neron.yaml non modifié" && \
		exit 1; \
	fi
	@echo ""
