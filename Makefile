#  Néron AI v2.2 — Makefile
# ============================================

BASE_DIR  := /mnt/usb-storage/neron/server
VENV      := $(BASE_DIR)/venv
PYTHON    := $(VENV)/bin/python3
PIP       := $(VENV)/bin/pip
SERVICE   := neron
LOG_DIR   := $(BASE_DIR)/logs
DATA_DIR  := $(BASE_DIR)/data
API_PORT  := 8010
API_KEY   := $(shell $(PYTHON) -c "import yaml; print(yaml.safe_load(open('$(BASE_DIR)/neron.yaml')).get('neron',{}).get('api_key',''))" 2>/dev/null)

# Colors for output
RED     := \033[0;31m
GREEN   := \033[0;32m
YELLOW  := \033[1;33m
BLUE    := \033[0;34m
NC      := \033[0m # No Color

.PHONY: all help install start stop restart status logs update clean \
		backup restore test neron version ollama telegram ha-agent agents \
		dev dev-stop dev-logs health check-deps format lint type-check \
		docker-build docker-run docker-stop setup-dev db-init db-migrate

# --- Défaut ---
all: help

help:
	@echo ""
	@echo "$(BLUE)╔══════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║         Néron AI v2.2 — Makefile         ║$(NC)"
	@echo "$(BLUE)╚══════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(YELLOW)[Installation / Maintenance]$(NC)"
	@echo "  make install    -- installer Néron"
	@echo "  make update     -- git pull + restart"
	@echo "  make clean      -- nettoyer venv et logs"
	@echo "  make version    -- versions Néron / Python / Ollama"
	@echo ""
	@echo "$(YELLOW)[Services]$(NC)"
	@echo "  make start      -- démarrer le service"
	@echo "  make stop       -- arrêter le service"
	@echo "  make restart    -- redémarrer le service"
	@echo "  make status     -- état du service systemd"
	@echo "  make logs       -- logs en direct"
	@echo "  make agents     -- état temps réel des agents"
	@echo ""
	@echo "$(YELLOW)[Développement]$(NC)"
	@echo "  make dev        -- démarrer en mode dev (avec reload)"
	@echo "  make dev-stop   -- arrêter le mode dev"
	@echo "  make dev-logs   -- logs du mode dev"
	@echo "  make format     -- formater le code (black)"
	@echo "  make lint       -- vérifier le code (ruff)"
	@echo "  make type-check -- vérifier les types (mypy)"
	@echo ""
	@echo "$(YELLOW)[Sauvegarde]$(NC)"
	@echo "  make backup     -- sauvegarder DB + neron.yaml"
	@echo "  make restore    -- restaurer une sauvegarde"
	@echo ""
	@echo "$(YELLOW)[Diagnostic]$(NC)"
	@echo "  make test       -- tester l'API et les agents"
	@echo "  make health     -- vérification santé complète"
	@echo "  make check-deps -- vérifier les dépendances"
	@echo "  make neron      -- afficher la config active"
	@echo ""
	@echo "$(YELLOW)[Intégration]$(NC)"
	@echo "  make ollama     -- gérer le modèle Ollama"
	@echo "  make telegram   -- configurer les bots Telegram"
	@echo "  make ha-agent   -- configurer Home Assistant"
	@echo ""
	@echo "$(YELLOW)[Docker]$(NC)"
	@echo "  make docker-build -- construire l'image Docker"
	@echo "  make docker-run   -- démarrer en Docker"
	@echo "  make docker-stop  -- arrêter Docker"
	@echo ""

# ── Installation ──────────────────────────────────────────────────────────────

install:
	@echo "$(GREEN)🔧 Installation de Néron AI v2.2...$(NC)"
	@echo ""
	@echo "$(BLUE)📦 Installation des dépendances système...$(NC)"
	@sudo apt-get update -qq
	@sudo apt-get install -y -qq \
		espeak \
		libespeak1 \
		ffmpeg \
		git \
		curl \
		tree \
		nano \
		make \
		python3-dev \
		python3-venv
	@echo "$(GREEN)✔ Dépendances système OK$(NC)"
	@echo "$(BLUE)🐍 Création du venv Python...$(NC)"
	@test -d $(VENV) || python3 -m venv $(VENV)
	@$(PIP) install --upgrade pip -q
	@$(PIP) install -r $(BASE_DIR)/requirements.txt -q
	@$(PIP) install -r $(BASE_DIR)/requirements-dev.txt -q
	@echo "$(GREEN)✔ Venv OK$(NC)"
	@mkdir -p $(LOG_DIR)
	@mkdir -p $(DATA_DIR)/world_model
	@mkdir -p $(DATA_DIR)/backups
	@echo "$(GREEN)✔ Dossiers data OK$(NC)"
	@echo "$(BLUE)⚙️  Configuration systemd...$(NC)"
	@sudo cp $(BASE_DIR)/neron.service /etc/systemd/system/neron.service 2>/dev/null || \
		echo "[Unit]\nDescription=Neron AI\nAfter=network.target\n\n[Service]\nType=simple\nUser=$$(whoami)\nWorkingDirectory=$(BASE_DIR)\nExecStart=$(PYTHON) $(BASE_DIR)/core/app.py\nRestart=always\nRestartSec=5\n\n[Install]\nWantedBy=multi-user.target" | sudo tee /etc/systemd/system/neron.service > /dev/null
	@sudo systemctl daemon-reload
	@sudo systemctl enable $(SERVICE)
	@echo "$(GREEN)✔ Service systemd activé$(NC)"
	@echo ""
	@echo "$(GREEN)✅ Installation terminée !$(NC)"
	@echo ""
	@echo "  👉 Configurez : $(YELLOW)nano $(BASE_DIR)/neron.yaml$(NC)"
	@echo "  👉 Démarrez   : $(YELLOW)make start$(NC)"
	@echo ""

# ── Développement ─────────────────────────────────────────────────────────────

setup-dev: check-deps
	@echo "$(BLUE)🔧 Configuration environnement dev...$(NC)"
	@$(PIP) install -r $(BASE_DIR)/requirements-dev.txt -q
	@mkdir -p $(BASE_DIR)/.vscode
	@echo "$(GREEN)✔ Environnement dev configuré$(NC)"

dev:
	@echo "$(GREEN)🚀 Démarrage en mode développement...$(NC)"
	@echo "$(YELLOW)Appuyez sur Ctrl+C pour arrêter$(NC)"
	@echo ""
	@source $(VENV)/bin/activate && \
		cd $(BASE_DIR) && \
		uvicorn core.agents.api_agent:app \
			--host 0.0.0.0 \
			--port $(API_PORT) \
			--reload \
			--log-level info \
			--access-log

dev-stop:
	@echo "$(YELLOW)🛑 Arrêt du mode développement...$(NC)"
	@pkill -f "uvicorn.*api_agent" || echo "Aucun processus dev trouvé"

dev-logs:
	@echo "$(BLUE)📋 Logs du mode développement:$(NC)"
	@tail -f $(BASE_DIR)/dev.log 2>/dev/null || echo "Pas de logs dev disponibles"

format:
	@echo "$(BLUE)🎨 Formatage du code...$(NC)"
	@black core/ tests/ --line-length 88
	@echo "$(GREEN)✔ Code formaté$(NC)"

lint:
	@echo "$(BLUE)🔍 Linting du code...$(NC)"
	@ruff check core/ tests/ --fix
	@echo "$(GREEN)✔ Linting terminé$(NC)"

type-check:
	@echo "$(BLUE)🔍 Vérification des types...$(NC)"
	@mypy core/ --config-file mypy.ini
	@echo "$(GREEN)✔ Types vérifiés$(NC)"

# ── Services ──────────────────────────────────────────────────────────────────

start:
	@echo "$(GREEN)▶  Démarrage de Néron...$(NC)"
	@sudo systemctl start $(SERVICE)
	@sleep 2
	@sudo systemctl is-active --quiet $(SERVICE) && \
		echo "$(GREEN)✔ Néron démarré$(NC)" || \
		(echo "$(RED)❌ Échec — make logs pour plus d'infos$(NC)" && exit 1)

stop:
	@echo "$(YELLOW)[stop] Arrêt de Néron...$(NC)"
	@sudo systemctl stop $(SERVICE) 2>/dev/null; true
	@echo "$(GREEN)✔ Néron arrêté$(NC)"

restart:
	@echo "$(BLUE)🔄 Redémarrage de Néron...$(NC)"
	@sudo systemctl restart $(SERVICE)
	@sleep 3
	@sudo systemctl is-active --quiet $(SERVICE) && \
		echo "$(GREEN)✔ Néron redémarré$(NC)" || \
		(echo "$(RED)❌ Échec — make logs pour plus d'infos$(NC)" && exit 1)

status:
	@echo ""
	@echo "$(BLUE)── Service systemd ──────────────────────────$(NC)"
	@sudo systemctl status $(SERVICE) --no-pager -l
	@echo ""
	@echo "$(BLUE)── Process actifs ───────────────────────────$(NC)"
	@ps aux | grep "python3 core/app.py" | grep -v grep | \
		awk '{printf "  PID %-7s  CPU %-5s  RAM %s\n", $$2, $$3, $$4}' || \
		echo "  Aucun process Néron détecté"
	@echo ""

logs:
	@sudo journalctl -u $(SERVICE) -f --no-pager

# ── Agents World Model ────────────────────────────────────────────────────────

agents:
	@echo ""
	@echo "$(BLUE)── État des agents (World Model) ────────────$(NC)"
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
	'$(GREEN)✅ online$(NC)' if v.get('status') == 'online' else '$(YELLOW)🟡 stale$(NC)' if v.get('status') == 'stale' else '$(RED)🔴 ' + str(v.get('status','')) + '$(NC)', \
	str(v.get('cpu','')) + '%' if v.get('cpu') else '-', \
	str(v.get('ram','')) + '%' if v.get('ram') else '-', \
	'latency=' + str(v.get('latency_ms','')) + 'ms' if v.get('latency_ms') else '' \
)) for name, v in agents.items()]; \
print('') \
" 2>/dev/null || echo "  $(RED)❌ API non disponible (make start ?)$(NC)"
	@echo ""

# ── Diagnostic ───────────────────────────────────────────────────────────────

health:
	@echo ""
	@echo "$(BLUE)🩺 Vérification santé complète$(NC)"
	@echo ""
	@echo "$(YELLOW)── API ──────────────────────────────────────$(NC)"
	@curl -sf http://localhost:$(API_PORT)/status > /dev/null && \
		echo "  $(GREEN)✔ /status répond$(NC)" || echo "  $(RED)❌ /status ne répond pas$(NC)"
	@curl -sf http://localhost:$(API_PORT)/ > /dev/null && \
		echo "  $(GREEN)✔ / (root) répond$(NC)" || echo "  $(RED)❌ / ne répond pas$(NC)"
	@echo ""
	@echo "$(YELLOW)── Ollama ───────────────────────────────────$(NC)"
	@curl -sf http://localhost:11434/api/tags > /dev/null && \
		echo "  $(GREEN)✔ Ollama répond$(NC)" || echo "  $(RED)❌ Ollama ne répond pas$(NC)"
	@echo ""
	@echo "$(YELLOW)── Process ──────────────────────────────────$(NC)"
	@PROCS=$$(ps aux | grep "python3 core/app.py" | grep -v grep | wc -l) && \
		echo "  $(GREEN)✔ $$PROCS process Néron actifs$(NC)"
	@echo ""
	@echo "$(YELLOW)── World Model ──────────────────────────────$(NC)"
	@test -f $(DATA_DIR)/world_model/agents_state.json && \
		echo "  $(GREEN)✔ agents_state.json présent$(NC)" || \
		echo "  $(YELLOW)⚠ agents_state.json absent (agents pas encore démarrés ?)$(NC)"
	@echo ""
	@echo "$(YELLOW)── Test LLM ─────────────────────────────────$(NC)"
	@curl -sf -X POST http://localhost:$(API_PORT)/input/text \
		-H "Content-Type: application/json" \
		-H "X-API-Key: $(API_KEY)" \
		-d '{"text":"ping"}' > /dev/null && \
		echo "  $(GREEN)✔ LLM répond$(NC)" || echo "  $(RED)❌ LLM ne répond pas$(NC)"
	@echo ""

check-deps:
	@echo "$(BLUE)🔍 Vérification des dépendances...$(NC)"
	@$(PYTHON) -c "import sys; print(f'Python: {sys.version}')";
	@command -v ollama >/dev/null 2>&1 && echo "$(GREEN)✔ Ollama installé$(NC)" || echo "$(RED)❌ Ollama non installé$(NC)"
	@ollama list >/dev/null 2>&1 && echo "$(GREEN)✔ Ollama fonctionne$(NC)" || echo "$(RED)❌ Ollama ne fonctionne pas$(NC)"
	@echo "$(GREEN)✔ Vérification terminée$(NC)"

test:
	@echo ""
	@echo "$(BLUE)🧪 Tests unitaires$(NC)"
	@echo ""
	@pytest tests/ -v --tb=short
	@echo ""

neron:
	@echo ""
	@echo "$(BLUE)⚙️  Configuration active (tokens masqués)$(NC)"
	@echo ""
	@grep -E "^[a-z_]+:" $(BASE_DIR)/neron.yaml | \
		grep -v "token\|TOKEN\|key\|KEY\|password\|PASSWORD" | \
		sed 's/^/  /'
	@echo ""

version:
	@echo ""
	@echo "$(BLUE)🧠 Néron AI$(NC)"
	@grep -m1 'VERSION' $(BASE_DIR)/core/agents/api_agent.py 2>/dev/null | \
		grep -o '"[0-9.]*"' | tr -d '"' | \
		awk '{print "  Version  : "$$1}' || echo "  Version  : inconnue"
	@echo "  Python   : $$($(PYTHON) --version 2>&1 | cut -d' ' -f2)"
	@echo "  Ollama   : $$(ollama --version 2>/dev/null | head -1 || echo 'non trouvé')"
	@echo "  Modèle   : $$($(PYTHON) -c "import yaml; print(yaml.safe_load(open('$(BASE_DIR)/neron.yaml'))['llm']['model'])" 2>/dev/null)"
	@echo "  Service  : $$(systemctl is-active neron 2>/dev/null || echo 'inactif')"
	@echo "  Process  : $$(ps aux | grep 'python3 core/app.py' | grep -v grep | wc -l) actifs"
	@echo ""

# ── Sauvegarde ────────────────────────────────────────────────────────────────

backup:
	@echo "$(BLUE)💾 Sauvegarde de Néron...$(NC)"
	@BACKUP_DIR=$(DATA_DIR)/backups/$$(date +%Y%m%d_%H%M%S) && \
		mkdir -p $$BACKUP_DIR && \
		cp $(BASE_DIR)/neron.yaml $$BACKUP_DIR/neron.yaml && \
		cp $(DATA_DIR)/memory.db $$BACKUP_DIR/memory.db 2>/dev/null || true && \
		cp $(DATA_DIR)/world_model/agents_state.json \
			$$BACKUP_DIR/agents_state.json 2>/dev/null || true && \
		echo "$(GREEN)✔ Sauvegarde créée : $$BACKUP_DIR$(NC)"

restore:
	@echo "$(BLUE)📂 Sauvegardes disponibles :$(NC)"
	@ls -lt $(DATA_DIR)/backups/ 2>/dev/null | grep "^d" | \
		awk '{print NR". "$$NF}' || echo "  Aucune sauvegarde trouvée"
	@echo ""
	@read -p "Nom du dossier à restaurer : " BACKUP && \
		test -d $(DATA_DIR)/backups/$$BACKUP || \
			(echo "$(RED)❌ Introuvable$(NC)" && exit 1) && \
		cp $(DATA_DIR)/backups/$$BACKUP/neron.yaml $(BASE_DIR)/neron.yaml && \
		cp $(DATA_DIR)/backups/$$BACKUP/memory.db \
			$(DATA_DIR)/memory.db 2>/dev/null || true && \
		echo "$(GREEN)✔ Restauration terminée — make restart pour appliquer$(NC)"

# ── Update ────────────────────────────────────────────────────────────────────

update:
	@echo "$(BLUE)🔄 Mise à jour de Néron...$(NC)"
	@git -C $(BASE_DIR) pull origin master
	@$(PIP) install -r $(BASE_DIR)/requirements.txt -q
	@sudo systemctl restart $(SERVICE)
	@sleep 3
	@sudo systemctl is-active --quiet $(SERVICE) && \
		echo "$(GREEN)✔ Néron mis à jour et redémarré$(NC)" || \
		echo "$(RED)❌ Échec au redémarrage — make logs$(NC)"

clean:
	@echo "$(YELLOW)🧹 Nettoyage...$(NC)"
	@read -p "Supprimer le venv et les logs ? [o/N] " confirm && \
		[ "$$confirm" = "o" ] || exit 0
	@rm -rf $(VENV)
	@rm -f $(LOG_DIR)/*.log
	@echo "$(GREEN)✔ Nettoyage terminé$(NC)"

# ── Intégrations ──────────────────────────────────────────────────────────────

ollama:
	@echo ""
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)  🦙 Gestion du modèle Ollama$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "$(YELLOW)  Modèles installés :$(NC)"
	@ollama list 2>/dev/null | tail -n +2 | awk '{print "  • "$$1}' || echo "  aucun"
	@echo ""
	@$(PYTHON) $(BASE_DIR)/scripts/ollama_recommend.py 2>/dev/null || true
	@echo ""
	@CURRENT=$$($(PYTHON) -c "import yaml; print(yaml.safe_load(open('$(BASE_DIR)/neron.yaml'))['llm']['model'])" 2>/dev/null || echo "llama3.2:3b") && \
		echo "$(YELLOW)  Modèle actuel : $$CURRENT$(NC)" && \
		echo "" && \
		read -p "  Entrée = garder $$CURRENT, ou tapez un modèle Ollama : " MODEL && \
		MODEL=$${MODEL:-$$CURRENT} && \
		echo "" && \
		echo "$(BLUE)📥 Téléchargement de $$MODEL...$(NC)" && \
		if ollama pull $$MODEL; then \
			echo "" && \
			echo "$(GREEN)✔ Téléchargement réussi$(NC)" && \
			$(PYTHON) -c "import yaml; \
f='$(BASE_DIR)/neron.yaml'; \
d=yaml.safe_load(open(f)); \
d['llm']['model']='$$MODEL'; \
yaml.dump(d,open(f,'w'),allow_unicode=True,default_flow_style=False); \
print('$(GREEN)✔ neron.yaml mis à jour : llm.model=$$MODEL$(NC)')" && \
			echo "" && \
			read -p "  Redémarrer Néron maintenant ? [O/n] " RESTART && \
			[ "$$RESTART" != "n" ] && $(MAKE) -C $(BASE_DIR) restart || \
				echo "  $(YELLOW)👉 make restart quand vous êtes prêt$(NC)"; \
		else \
			echo "" && \
			echo "$(RED)❌ Échec du téléchargement — neron.yaml non modifié$(NC)"; \
		fi

telegram:
	@bash $(BASE_DIR)/install.sh --telegram-only

ha-agent:
	@echo ""
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)  🏠 Configuration Home Assistant$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@CURRENT_URL=$$($(PYTHON) -c "import yaml; d=yaml.safe_load(open('$(BASE_DIR)/neron.yaml')); print(d.get('home_assistant',{}).get('url','http://homeassistant.local:8123'))") && \
	CURRENT_ENABLED=$$($(PYTHON) -c "import yaml; d=yaml.safe_load(open('$(BASE_DIR)/neron.yaml')); print(d.get('home_assistant',{}).get('enabled',False))") && \
	echo "$(YELLOW)  État actuel  : $$CURRENT_ENABLED$(NC)" && \
	echo "$(YELLOW)  URL actuelle : $$CURRENT_URL$(NC)" && \
	echo "" && \
	read -p "  URL Home Assistant [$$CURRENT_URL] : " HA_URL && \
	HA_URL=$${HA_URL:-$$CURRENT_URL} && \
	echo "" && \
	echo "$(YELLOW)  👉 Générez un token dans HA :$(NC)" && \
	echo "     Profil → Sécurité → Tokens d'accès longue durée" && \
	echo "" && \
	read -p "  Token (laisser vide pour garder l'actuel) : " HA_TOKEN && \
	if [ -z "$$HA_TOKEN" ]; then \
		HA_TOKEN=$$($(PYTHON) -c "import yaml; d=yaml.safe_load(open('$(BASE_DIR)/neron.yaml')); print(d.get('home_assistant',{}).get('token',''))"); \
	fi && \
	echo "" && \
	echo "$(BLUE)🔍 Test de connexion vers $$HA_URL...$(NC)" && \
	HTTP_CODE=$$(curl -s -o /dev/null -w "%{http_code}" \
		-H "Authorization: Bearer $$HA_TOKEN" \
		$$HA_URL/api/) && \
	if [ "$$HTTP_CODE" = "200" ]; then \
		echo "$(GREEN)✔ Connexion réussie (HTTP $$HTTP_CODE)$(NC)" && \
		$(PYTHON) $(BASE_DIR)/scripts/ha_setup.py \
			"$(BASE_DIR)/neron.yaml" "$$HA_URL" "$$HA_TOKEN" && \
		echo "" && \
		read -p "  Redémarrer Néron maintenant ? [O/n] " RESTART && \
		[ "$$RESTART" != "n" ] && $(MAKE) -C $(BASE_DIR) restart || \
			echo "  $(YELLOW)👉 make restart quand vous êtes prêt$(NC)"; \
	else \
		echo "$(RED)❌ Connexion échouée (HTTP $$HTTP_CODE)$(NC)" && \
		echo "  Vérifiez l'URL et le token — neron.yaml non modifié" && \
		exit 1; \
	fi
	@echo ""

# ── Docker ────────────────────────────────────────────────────────────────────

docker-build:
	@echo "$(BLUE)🐳 Construction de l'image Docker...$(NC)"
	@docker build -t neron-ai:$(shell git rev-parse --short HEAD 2>/dev/null || echo "latest") $(BASE_DIR)
	@echo "$(GREEN)✔ Image Docker construite$(NC)"

docker-run:
	@echo "$(GREEN)🐳 Démarrage de Néron en Docker...$(NC)"
	@docker run -d --name neron-ai \
		-p $(API_PORT):$(API_PORT) \
		-v $(BASE_DIR)/data:/app/data \
		-v $(BASE_DIR)/logs:/app/logs \
		neron-ai:$(shell git rev-parse --short HEAD 2>/dev/null || echo "latest")
	@echo "$(GREEN)✔ Néron démarré en Docker$(NC)"

docker-stop:
	@echo "$(YELLOW)🐳 Arrêt de Docker...$(NC)"
	@docker stop neron-ai 2>/dev/null || true
	@docker rm neron-ai 2>/dev/null || true
	@echo "$(GREEN)✔ Docker arrêté$(NC)"

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
