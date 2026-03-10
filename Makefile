# ============================================
#  Néron AI v2.1 — Makefile
# ============================================

BASE_DIR  := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
VENV      := $(BASE_DIR)/venv
PYTHON    := $(VENV)/bin/python3
PIP       := $(VENV)/bin/pip
SERVICE   := neron
LOG_DIR   := $(BASE_DIR)/logs
YAML      := $(BASE_DIR)/neron.yaml

# Helper pour lire neron.yaml
YAML_GET  = $(PYTHON) -c "import yaml; d=yaml.safe_load(open('$(YAML)')); print(d.get('$(1)',{}).get('$(2)','$(3)'))" 2>/dev/null || echo "$(3)"

.PHONY: install start stop restart status logs update help clean \
        backup restore test ollama telegram env version

# --- Défaut ---
all: help

help:
	@echo ""
	@echo "  🧠 Néron AI v2.1 — Commandes disponibles"
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
	@echo "  make backup     — sauvegarder DB + neron.yaml"
	@echo "  make restore    — restaurer une sauvegarde"
	@echo "  make test       — tester l'API et Ollama"
	@echo "  make ollama     — gérer le modèle Ollama"
	@echo "  make telegram   — configurer les bots Telegram"
	@echo "  make env        — afficher la config active"
	@echo "  make version    — versions Néron / Python / Ollama"
	@echo ""

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
		make \
		python3-yaml
	@echo "✔ Dépendances système OK"
	@echo "🐍 Création du venv Python..."
	@test -d $(VENV) || python3 -m venv $(VENV)
	@$(PIP) install --upgrade pip -q
	@$(PIP) install -r $(BASE_DIR)/requirements.txt -q
	@echo "✔ Venv OK"
	@mkdir -p $(LOG_DIR)
	@mkdir -p $(BASE_DIR)/data
	@echo "✔ Dossiers OK"
	@test -f $(YAML) || cp $(BASE_DIR)/neron.yaml.example $(YAML)
	@echo "✔ neron.yaml OK"
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
	@echo "  👉 Éditez votre config : nano $(YAML)"
	@echo "  👉 Puis lancez         : make start"
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
		cp $(YAML) $$BACKUP_DIR/neron.yaml && \
		cp $(BASE_DIR)/data/memory.db $$BACKUP_DIR/memory.db 2>/dev/null || true && \
		echo "✔ Sauvegarde créée : $$BACKUP_DIR"

restore:
	@echo "📂 Sauvegardes disponibles :"
	@ls -lt $(BASE_DIR)/backups/ 2>/dev/null | grep "^d" | awk '{print NR". "$$NF}' || echo "  Aucune sauvegarde trouvée"
	@echo ""
	@read -p "Nom du dossier à restaurer : " BACKUP && \
		test -d $(BASE_DIR)/backups/$$BACKUP || (echo "❌ Introuvable" && exit 1) && \
		cp $(BASE_DIR)/backups/$$BACKUP/neron.yaml $(YAML) && \
		cp $(BASE_DIR)/backups/$$BACKUP/memory.db $(BASE_DIR)/data/memory.db 2>/dev/null || true && \
		echo "✔ Restauration terminée — make restart pour appliquer"

test:
	@echo "🧪 Test de l'API Néron..."
	@PORT=$$($(PYTHON) -c "import yaml; d=yaml.safe_load(open('$(YAML)')); print(d.get('server',{}).get('port',8000))" 2>/dev/null || echo 8000) && \
		curl -sf http://localhost:$$PORT/health > /dev/null && \
		echo "✔ Core API répond (port $$PORT)" || echo "❌ Core API ne répond pas"
	@curl -sf http://localhost:11434/api/tags > /dev/null && \
		echo "✔ Ollama répond" || echo "❌ Ollama ne répond pas"

env:
	@echo ""
	@echo "  ⚙️  Configuration active (neron.yaml — tokens masqués)"
	@echo ""
	@$(PYTHON) -c " \
import yaml; \
d = yaml.safe_load(open('$(YAML)')); \
sections = ['neron','server','llm','stt','tts','memory','watchdog']; \
[print(f'  [{s}]') or \
 [print(f'    {k}: {\"****\" if any(x in k for x in [\"token\",\"key\",\"secret\"]) else v}') \
  for k,v in d.get(s,{}).items()] \
 for s in sections if s in d] \
" 2>/dev/null
	@echo ""

version:
	@echo ""
	@echo "  🧠 Néron AI"
	@grep -m1 "^VERSION" $(BASE_DIR)/modules/neron_core/app.py 2>/dev/null | \
		cut -d'"' -f2 | awk '{print "  Version  : "$$1}' || echo "  Version  : inconnue"
	@echo "  Python   : $$(python3 --version 2>&1 | cut -d' ' -f2)"
	@echo "  Ollama   : $$(ollama --version 2>/dev/null || echo 'non trouvé')"
	@MODEL=$$($(PYTHON) -c "import yaml; d=yaml.safe_load(open('$(YAML)')); print(d.get('llm',{}).get('model','?'))" 2>/dev/null || echo '?') && \
		echo "  Modèle   : $$MODEL"
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
	@CURRENT=$$($(PYTHON) -c "import yaml; d=yaml.safe_load(open('$(YAML)')); print(d.get('llm',{}).get('model','llama3.2:1b'))" 2>/dev/null || echo 'llama3.2:1b') && \
		echo "  Modèle actuel : $$CURRENT" && \
		echo "" && \
		read -p "  Entrée = garder $$CURRENT, ou tapez un nouveau modèle : " MODEL && \
		MODEL=$${MODEL:-$$CURRENT} && \
		echo "" && \
		echo "📥 Téléchargement de $$MODEL..." && \
		if ollama pull $$MODEL; then \
			echo "" && \
			echo "✔ Téléchargement réussi" && \
			$(PYTHON) -c " \
import yaml; \
path='$(YAML)'; \
d=yaml.safe_load(open(path)); \
d.setdefault('llm',{})['model']='$$MODEL'; \
yaml.dump(d, open(path,'w'), allow_unicode=True, default_flow_style=False) \
" && \
			echo "✔ neron.yaml mis à jour : llm.model=$$MODEL" && \
			echo "" && \
			read -p "  Redémarrer Néron maintenant ? [O/n] " RESTART && \
			[ "$$RESTART" != "n" ] && $(MAKE) -C $(BASE_DIR) restart || echo "  👉 make restart quand vous êtes prêt"; \
		else \
			echo "" && \
			echo "❌ Échec du téléchargement — neron.yaml non modifié"; \
		fi

telegram:
	@bash $(BASE_DIR)/install.sh --telegram-only
