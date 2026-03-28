#  Néron AI v2.2 — Makefile
# ============================================

BASE_DIR  := /mnt/usb-storage/neron/server
VENV      := $(BASE_DIR)/venv
PYTHON    := $(VENV)/bin/python3
PIP       := $(VENV)/bin/pip
SERVICE   := neron
LOG_DIR   := $(BASE_DIR)/data/logs
API_PORT  := 8010
API_KEY   := $(shell $(PYTHON) -c "import yaml; print(yaml.safe_load(open('$(BASE_DIR)/neron.yaml')).get('neron',{}).get('api_key',''))" 2>/dev/null)

.PHONY: all help install start stop restart status logs update clean \
		backup restore test neron version ollama telegram ha-agent agents

# --- Défaut ---
all: help

help:
	@echo ""
	@echo "╔══════════════════════════════════════════╗"
	@echo "║         Néron AI v2.2 — Makefile         ║"
	@echo "╚══════════════════════════════════════════╝"
	@echo ""
	@echo "[Installation / Maintenance]"
	@echo "  make install    -- installer Néron"
	@echo "  make update     -- git pull + restart"
	@echo "  make clean      -- nettoyer venv et logs"
	@echo "  make version    -- versions Néron / Python / Ollama"
	@echo ""
	@echo "[Services]"
	@echo "  make start      -- démarrer le service"
	@echo "  make stop       -- arrêter le service"
	@echo "  make restart    -- redémarrer le service"
	@echo "  make status     -- état du service systemd"
	@echo "  make logs       -- logs en direct"
	@echo "  make agents     -- état temps réel des agents"
	@echo ""
	@echo "[Sauvegarde]"
	@echo "  make backup     -- sauvegarder DB + neron.yaml"
	@echo "  make restore    -- restaurer une sauvegarde"
	@echo ""
	@echo "[Diagnostic]"
	@echo "  make test       -- tester l'API et les agents"
	@echo "  make quality    -- vérifier qualité du code (lint, type, format)"
	@echo "  make coverage   -- rapport de couverture des tests"
	@echo "  make neron      -- afficher la config active"
	@echo ""
	@echo "[Intégration]"
	@echo "  make ollama     -- gérer le modèle Ollama"
	@echo "  make telegram   -- configurer les bots Telegram"
	@echo "  make ha-agent   -- configurer Home Assistant"
	@echo ""

# ── Installation ──────────────────────────────────────────────────────────────

install:
	@echo "🔧 Installation de Néron AI v2.2..."
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
	@mkdir -p $(BASE_DIR)/data/world_model
	@echo "✔ Dossiers data OK"
	@echo "⚙️  Configuration systemd..."
	@echo "[Unit]"
	@sudo cp /tmp/neron.service /etc/systemd/system/neron.service
	@sudo systemctl daemon-reload
	@sudo systemctl enable $(SERVICE)
	@echo "✔ Service systemd activé"
	@echo ""
	@echo "✅ Installation terminée !"
	@echo ""
	@echo "  👉 Configurez : nano $(BASE_DIR)/neron.yaml"
	@echo "  👉 Démarrez   : make start"
	@echo ""

# ── Services ──────────────────────────────────────────────────────────────────

start:
	@echo "▶  Démarrage de Néron..."
	@sudo systemctl start $(SERVICE)
	@sleep 2
	@sudo systemctl is-active --quiet $(SERVICE) && \
		echo "✔ Néron démarré" || \
		(echo "❌ Échec — make logs pour plus d'infos" && exit 1)

stop:
	@echo "[stop] Arrêt de Néron..."
	@sudo systemctl stop $(SERVICE) 2>/dev/null; true
	@echo "✔ Néron arrêté"

restart:
	@echo "🔄 Redémarrage de Néron..."
	@sudo systemctl restart $(SERVICE)
	@sleep 3
	@sudo systemctl is-active --quiet $(SERVICE) && \
		echo "✔ Néron redémarré" || \
		(echo "❌ Échec — make logs pour plus d'infos" && exit 1)

status:
	@echo ""
	@echo "── Service systemd ──────────────────────────"
	@sudo systemctl status $(SERVICE) --no-pager -l
	@echo ""
	@echo "── Process actifs ───────────────────────────"
	@ps aux | grep "python3 core/app.py" | grep -v grep | \
		awk '{printf "  PID %-7s  CPU %-5s  RAM %s\n", $$2, $$3, $$4}' || \
		echo "  Aucun process Néron détecté"
	@echo ""

logs:
	@sudo journalctl -u $(SERVICE) -f --no-pager

# ── Agents World Model ────────────────────────────────────────────────────────

agents:
	@echo ""
	@echo "── État des agents (World Model) ────────────"
	@curl -sf http://localhost:$(API_PORT)/status/agents \
		-H "X-API-Key: $(API_KEY)" | \
		$(PYTHON) -c "\
import sys, json, time; \
d = json.load(sys.stdin); \
agents = d.get('agents', {}); \
now = time.time(); \
print(''); \
[print('  {:15s} {:8s}  CPU={:<5}  RAM={:<5}  {}'.format( \
	name, \
	'✅ online' if v.get('status') == 'online' else '🟡 stale' if v.get('status') == 'stale' else '🔴 ' + str(v.get('status','')), \
	str(v.get('cpu','')) + '%' if v.get('cpu') else '-', \
	str(v.get('ram','')) + '%' if v.get('ram') else '-', \
	'latency=' + str(v.get('latency_ms','')) + 'ms' if v.get('latency_ms') else '' \
)) for name, v in agents.items()]; \
print('') \
" 2>/dev/null || echo "  ❌ API non disponible (make start ?)"
	@echo ""

# ── Diagnostic ───────────────────────────────────────────────────────────────

test:
	@echo ""
	@echo "🧪 Diagnostic Néron v2.2"
	@echo ""
	@echo "── API ──────────────────────────────────────"
	@curl -sf http://localhost:$(API_PORT)/health > /dev/null && \
		echo "  ✔ /health répond" || echo "  ❌ /health ne répond pas"
	@curl -sf http://localhost:$(API_PORT)/status/agents \
		-H "X-API-Key: $(API_KEY)" > /dev/null && \
		echo "  ✔ /status/agents répond" || echo "  ❌ /status/agents ne répond pas"
	@echo ""
	@echo "── Ollama ───────────────────────────────────"
	@curl -sf http://localhost:11434/api/tags > /dev/null && \
		echo "  ✔ Ollama répond" || echo "  ❌ Ollama ne répond pas"
	@echo ""
	@echo "── Process ──────────────────────────────────"
	@PROCS=$$(ps aux | grep "python3 core/app.py" | grep -v grep | wc -l) && \
		echo "  ✔ $$PROCS process Néron actifs"
	@echo ""
	@echo "── World Model ──────────────────────────────"
	@test -f $(BASE_DIR)/data/world_model/agents_state.json && \
		echo "  ✔ agents_state.json présent" || \
		echo "  ⚠ agents_state.json absent (agents pas encore démarrés ?)"
	@echo ""
	@echo "── Test LLM ─────────────────────────────────"
	@curl -sf -X POST http://localhost:$(API_PORT)/input/text \
		-H "Content-Type: application/json" \
		-H "X-API-Key: $(API_KEY)" \
		-d '{"text":"ping"}' > /dev/null && \
		echo "  ✔ LLM répond" || echo "  ❌ LLM ne répond pas"
	@echo ""

neron:
	@echo ""
	@echo "  ⚙️  Configuration active (tokens masqués)"
	@echo ""
	@grep -E "^[a-z_]+:" $(BASE_DIR)/neron.yaml | \
		grep -v "token\|TOKEN\|key\|KEY\|password\|PASSWORD" | \
		sed 's/^/  /'
	@echo ""

quality:
	@echo ""
	@echo "  🔍 Vérification qualité du code"
	@echo ""
	@echo "── Linting (ruff) ──────────────────────────"
	@ruff check core/ || echo "  ❌ Erreurs de linting"
	@echo ""
	@echo "── Format (black) ──────────────────────────"
	@black --check --quiet core/ && echo "  ✔ Code formaté" || echo "  ❌ Code mal formaté"
	@echo ""
	@echo "── Types (mypy) ────────────────────────────"
	@mypy core/ --config-file mypy.ini || echo "  ❌ Erreurs de types"
	@echo ""

coverage:
	@echo ""
	@echo "  📊 Couverture des tests"
	@echo ""
	@pytest --cov=core --cov-report=term-missing --cov-report=html
	@echo ""
	@echo "Rapport HTML: file://$(BASE_DIR)/htmlcov/index.html"

test:
	@echo ""
	@echo "  🧪 Tests unitaires"
	@echo ""
	@pytest tests/ -v --tb=short
	@echo ""

version:
	@echo ""
	@echo "  🧠 Néron AI"
	@grep -m1 'VERSION' $(BASE_DIR)/core/agents/api_agent.py 2>/dev/null | \
		grep -o '"[0-9.]*"' | tr -d '"' | \
		awk '{print "  Version  : "$$1}' || echo "  Version  : inconnue"
	@echo "  Python   : $$($(PYTHON) --version 2>&1 | cut -d' ' -f2)"
	@echo "  Ollama   : $$(ollama --version 2>/dev/null | head -1 || echo 'non trouvé')"
	@echo "  Modèle   : $$($(PYTHON) -c "import yaml; d=yaml.safe_load(open('$(BASE_DIR)/neron.yaml')); print(d.get('llm',{}).get('model','?'))" 2>/dev/null)"
	@echo "  Service  : $$(systemctl is-active neron 2>/dev/null || echo 'inactif')"
	@echo "  Process  : $$(ps aux | grep 'python3 core/app.py' | grep -v grep | wc -l) actifs"
	@echo ""

# ── Sauvegarde ────────────────────────────────────────────────────────────────

backup:
	@echo "💾 Sauvegarde de Néron..."
	@BACKUP_DIR=$(BASE_DIR)/backups/$$(date +%Y%m%d_%H%M%S) && \
		mkdir -p $$BACKUP_DIR && \
		cp $(BASE_DIR)/neron.yaml $$BACKUP_DIR/neron.yaml && \
		cp $(BASE_DIR)/data/memory.db $$BACKUP_DIR/memory.db 2>/dev/null || true && \
		cp $(BASE_DIR)/data/world_model/agents_state.json \
			$$BACKUP_DIR/agents_state.json 2>/dev/null || true && \
		echo "✔ Sauvegarde créée : $$BACKUP_DIR"

restore:
	@echo "📂 Sauvegardes disponibles :"
	@ls -lt $(BASE_DIR)/backups/ 2>/dev/null | grep "^d" | \
		awk '{print NR". "$$NF}' || echo "  Aucune sauvegarde trouvée"
	@echo ""
	@read -p "Nom du dossier à restaurer : " BACKUP && \
		test -d $(BASE_DIR)/backups/$$BACKUP || \
			(echo "❌ Introuvable" && exit 1) && \
		cp $(BASE_DIR)/backups/$$BACKUP/neron.yaml $(BASE_DIR)/neron.yaml && \
		cp $(BASE_DIR)/backups/$$BACKUP/memory.db \
			$(BASE_DIR)/data/memory.db 2>/dev/null || true && \
		echo "✔ Restauration terminée — make restart pour appliquer"

# ── Update ────────────────────────────────────────────────────────────────────

update:
	@echo "🔄 Mise à jour de Néron..."
	@git -C $(BASE_DIR) pull origin master
	@$(PIP) install -r $(BASE_DIR)/requirements.txt -q
	@sudo systemctl restart $(SERVICE)
	@sleep 3
	@sudo systemctl is-active --quiet $(SERVICE) && \
		echo "✔ Néron mis à jour et redémarré" || \
		echo "❌ Échec au redémarrage — make logs"

clean:
	@echo "🧹 Nettoyage..."
	@read -p "Supprimer le venv et les logs ? [o/N] " confirm && \
		[ "$$confirm" = "o" ] || exit 0
	@rm -rf $(VENV)
	@rm -f $(LOG_DIR)/*.log
	@echo "✔ Nettoyage terminé"

# ── Intégrations ──────────────────────────────────────────────────────────────

ollama:
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  🦙 Gestion du modèle Ollama"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "  Modèles installés :"
	@ollama list 2>/dev/null | tail -n +2 | awk '{print "  • "$$1}' || echo "  aucun"
	@echo ""
	@$(PYTHON) $(BASE_DIR)/scripts/ollama_recommend.py 2>/dev/null || true
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
			$(PYTHON) -c "import yaml; \
f='$(BASE_DIR)/neron.yaml'; \
d=yaml.safe_load(open(f)); \
d['llm']['model']='$$MODEL'; \
yaml.dump(d,open(f,'w'),allow_unicode=True,default_flow_style=False); \
print('✔ neron.yaml mis à jour : llm.model=$$MODEL')" && \
			echo "" && \
			read -p "  Redémarrer Néron maintenant ? [O/n] " RESTART && \
			[ "$$RESTART" != "n" ] && $(MAKE) -C $(BASE_DIR) restart || \
				echo "  👉 make restart quand vous êtes prêt"; \
		else \
			echo "" && \
			echo "❌ Échec du téléchargement — neron.yaml non modifié"; \
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
		$(PYTHON) $(BASE_DIR)/scripts/ha_setup.py \
			"$(BASE_DIR)/neron.yaml" "$$HA_URL" "$$HA_TOKEN" && \
		echo "" && \
		read -p "  Redémarrer Néron maintenant ? [O/n] " RESTART && \
		[ "$$RESTART" != "n" ] && $(MAKE) -C $(BASE_DIR) restart || \
			echo "  👉 make restart quand vous êtes prêt"; \
	else \
		echo "❌ Connexion échouée (HTTP $$HTTP_CODE)" && \
		echo "  Vérifiez l'URL et le token — neron.yaml non modifié" && \
		exit 1; \
	fi
	@echo ""
