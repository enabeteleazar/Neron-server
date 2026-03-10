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

# --- Couleurs tput ---
BOLD  := $(shell tput bold 2>/dev/null || echo '')
RESET := $(shell tput sgr0 2>/dev/null || echo '')
RED   := $(shell tput setaf 1 2>/dev/null || echo '')
GREEN := $(shell tput setaf 2 2>/dev/null || echo '')
YELLOW:= $(shell tput setaf 3 2>/dev/null || echo '')
BLUE  := $(shell tput setaf 4 2>/dev/null || echo '')
CYAN  := $(shell tput setaf 6 2>/dev/null || echo '')

# --- Helpers affichage ---
OK    = echo "  $(GREEN)$(BOLD)✔$(RESET) $(1)"
FAIL  = echo "  $(RED)$(BOLD)✘$(RESET) $(1)" && exit 1
WARN  = echo "  $(YELLOW)⚠$(RESET)  $(1)"
STEP  = echo "\n$(BLUE)$(BOLD)▶$(RESET) $(1)"
SEP   = echo "$(CYAN)$(BOLD)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(RESET)"

# --- Spinner shell ---
SPINNER = bash -c '\
    pid=$$1; spinstr="|/-\\\\"; \
    while kill -0 $$pid 2>/dev/null; do \
        c=$${spinstr:0:1}; spinstr=$${spinstr:1}$$c; \
        printf " $(BLUE)[%s]$(RESET)\r" "$$c"; sleep 0.1; \
    done; printf "        \r"' -- 

# Helper yaml
YAML_GET = $(PYTHON) -c "import yaml; d=yaml.safe_load(open('$(YAML)')); print(d.get('$(1)',{}).get('$(2)','$(3)'))" 2>/dev/null || echo "$(3)"

.PHONY: install start stop restart status logs update help clean \
        backup restore test ollama telegram env version

all: help

help:
	@$(SEP)
	@echo "  $(BOLD)$(BLUE)🧠 Néron AI v2.1 — Commandes$(RESET)"
	@$(SEP)
	@echo ""
	@echo "  $(BOLD)make install$(RESET)    — installer Néron (deps, venv, systemd)"
	@echo "  $(BOLD)make start$(RESET)      — démarrer le service"
	@echo "  $(BOLD)make stop$(RESET)       — arrêter le service"
	@echo "  $(BOLD)make restart$(RESET)    — redémarrer le service"
	@echo "  $(BOLD)make status$(RESET)     — état du service"
	@echo "  $(BOLD)make logs$(RESET)       — logs en direct"
	@echo "  $(BOLD)make update$(RESET)     — git pull + restart"
	@echo "  $(BOLD)make clean$(RESET)      — nettoyer venv et logs"
	@echo ""
	@echo "  $(BOLD)make backup$(RESET)     — sauvegarder DB + neron.yaml"
	@echo "  $(BOLD)make restore$(RESET)    — restaurer une sauvegarde"
	@echo "  $(BOLD)make test$(RESET)       — tester l'API et Ollama"
	@echo "  $(BOLD)make ollama$(RESET)     — gérer le modèle Ollama"
	@echo "  $(BOLD)make telegram$(RESET)   — configurer les bots Telegram"
	@echo "  $(BOLD)make env$(RESET)        — afficher la config active"
	@echo "  $(BOLD)make version$(RESET)    — versions Néron / Python / Ollama"
	@echo ""

install:
	@$(SEP)
	@echo "  $(BOLD)$(BLUE)🔧 Installation de Néron AI$(RESET)"
	@$(SEP)
	@echo ""
	@$(call STEP,"Dépendances système...")
	@sudo apt-get update -qq > /dev/null 2>&1 & $(SPINNER) $$!
	@sudo apt-get install -y -qq \
		espeak libespeak1 ffmpeg \
		git curl tree nano make \
		python3-yaml > /dev/null 2>&1 & $(SPINNER) $$!
	@$(call OK,"Dépendances système OK")
	@$(call STEP,"Création du venv Python...")
	@test -d $(VENV) || python3 -m venv $(VENV)
	@$(PIP) install --upgrade pip -q > /dev/null 2>&1 & $(SPINNER) $$!
	@$(PIP) install -r $(BASE_DIR)/requirements.txt -q > /dev/null 2>&1 & $(SPINNER) $$!
	@$(call OK,"Venv Python OK")
	@mkdir -p $(LOG_DIR) $(BASE_DIR)/data
	@$(call OK,"Dossiers OK")
	@test -f $(YAML) || cp $(BASE_DIR)/neron.yaml.example $(YAML)
	@$(call OK,"neron.yaml OK")
	@$(call STEP,"Configuration systemd...")
	@sed -e "s|__NERON_DIR__|$(BASE_DIR)|g" \
		-e "s|__NERON_USER__|$(shell whoami)|g" \
		$(BASE_DIR)/neron.service > /tmp/neron.service
	@sudo cp /tmp/neron.service /etc/systemd/system/neron.service
	@rm /tmp/neron.service
	@sudo systemctl daemon-reload
	@sudo systemctl enable $(SERVICE) > /dev/null 2>&1
	@$(call OK,"Service systemd activé")
	@echo ""
	@$(SEP)
	@echo "  $(GREEN)$(BOLD)✅ Installation terminée !$(RESET)"
	@$(SEP)
	@echo ""
	@echo "  $(BOLD)1.$(RESET) Configurez : $(YELLOW)nano $(YAML)$(RESET)"
	@echo "  $(BOLD)2.$(RESET) Lancez     : $(YELLOW)make start$(RESET)"
	@echo ""

start:
	@$(call STEP,"Démarrage de Néron...")
	@sudo systemctl start $(SERVICE)
	@sleep 2
	@sudo systemctl is-active --quiet $(SERVICE) && \
		$(call OK,"Néron démarré") || \
		($(call FAIL,"Échec — make logs pour plus d'infos"))

stop:
	@$(call STEP,"Arrêt de Néron...")
	@sudo systemctl stop $(SERVICE)
	@$(call OK,"Néron arrêté")

restart:
	@$(call STEP,"Redémarrage de Néron...")
	@sudo systemctl restart $(SERVICE)
	@sleep 2
	@sudo systemctl is-active --quiet $(SERVICE) && \
		$(call OK,"Néron redémarré") || \
		($(call FAIL,"Échec — make logs pour plus d'infos"))

status:
	@echo ""
	@$(SEP)
	@echo "  $(BOLD)$(BLUE)📊 Statut du service$(RESET)"
	@$(SEP)
	@sudo systemctl status $(SERVICE) --no-pager

logs:
	@echo "  $(CYAN)📋 Logs en direct — Ctrl+C pour quitter$(RESET)"
	@echo ""
	@sudo journalctl -u $(SERVICE) -f

update:
	@$(call STEP,"Mise à jour de Néron...")
	@git -C $(BASE_DIR) pull origin master > /dev/null 2>&1 & $(SPINNER) $$!
	@$(call OK,"Code mis à jour")
	@$(PIP) install -r $(BASE_DIR)/requirements.txt -q > /dev/null 2>&1 & $(SPINNER) $$!
	@$(call OK,"Dépendances mises à jour")
	@sudo systemctl restart $(SERVICE)
	@sleep 2
	@sudo systemctl is-active --quiet $(SERVICE) && \
		$(call OK,"Néron redémarré") || \
		$(call WARN,"Échec au redémarrage")

clean:
	@$(call STEP,"Nettoyage...")
	@read -p "  Supprimer le venv et les logs ? [o/N] " confirm && \
		[ "$$confirm" = "o" ] || exit 0
	@rm -rf $(VENV)
	@rm -f $(LOG_DIR)/*.log
	@$(call OK,"Nettoyage terminé")

backup:
	@$(call STEP,"Sauvegarde de Néron...")
	@BACKUP_DIR=$(BASE_DIR)/backups/$$(date +%Y%m%d_%H%M%S) && \
		mkdir -p $$BACKUP_DIR && \
		cp $(YAML) $$BACKUP_DIR/neron.yaml && \
		cp $(BASE_DIR)/data/memory.db $$BACKUP_DIR/memory.db 2>/dev/null || true && \
		$(call OK,"Sauvegarde créée : $$BACKUP_DIR")

restore:
	@$(call STEP,"Restauration...")
	@echo "  $(BOLD)Sauvegardes disponibles :$(RESET)"
	@ls -lt $(BASE_DIR)/backups/ 2>/dev/null | grep "^d" | awk '{print "  "NR". "$$NF}' || \
		$(call WARN,"Aucune sauvegarde trouvée")
	@echo ""
	@read -p "  Nom du dossier à restaurer : " BACKUP && \
		test -d $(BASE_DIR)/backups/$$BACKUP || ($(call FAIL,"Introuvable")) && \
		cp $(BASE_DIR)/backups/$$BACKUP/neron.yaml $(YAML) && \
		cp $(BASE_DIR)/backups/$$BACKUP/memory.db $(BASE_DIR)/data/memory.db 2>/dev/null || true && \
		$(call OK,"Restauration terminée — make restart pour appliquer")

test:
	@$(SEP)
	@echo "  $(BOLD)$(BLUE)🧪 Test de l'API Néron$(RESET)"
	@$(SEP)
	@echo ""
	@PORT=$$($(PYTHON) -c "import yaml; d=yaml.safe_load(open('$(YAML)')); print(d.get('server',{}).get('port',8000))" 2>/dev/null || echo 8000) && \
		curl -sf http://localhost:$$PORT/health > /dev/null && \
		$(call OK,"Core API répond (port $$PORT)") || \
		$(call WARN,"Core API ne répond pas")
	@curl -sf http://localhost:11434/api/tags > /dev/null && \
		$(call OK,"Ollama répond") || \
		$(call WARN,"Ollama ne répond pas")
	@echo ""

env:
	@$(SEP)
	@echo "  $(BOLD)$(BLUE)⚙️  Configuration active$(RESET) $(YELLOW)(tokens masqués)$(RESET)"
	@$(SEP)
	@echo ""
	@$(PYTHON) -c "\
import yaml; \
d = yaml.safe_load(open('$(YAML)')); \
sections = ['neron','server','llm','stt','tts','memory','watchdog']; \
[print(f'  \033[1m[{s}]\033[0m') or \
 [print(f'    {k}: {\"****\" if any(x in k for x in [\"token\",\"key\",\"secret\"]) else v}') \
  for k,v in d.get(s,{}).items()] \
 for s in sections if s in d]" 2>/dev/null
	@echo ""

version:
	@$(SEP)
	@echo "  $(BOLD)$(BLUE)🧠 Néron AI — Versions$(RESET)"
	@$(SEP)
	@echo ""
	@grep -m1 "^VERSION" $(BASE_DIR)/modules/neron_core/app.py 2>/dev/null | \
		cut -d'"' -f2 | awk '{print "  Version  : "$$1}' || echo "  Version  : inconnue"
	@echo "  Python   : $$(python3 --version 2>&1 | cut -d' ' -f2)"
	@echo "  Ollama   : $$(ollama --version 2>/dev/null || echo 'non trouvé')"
	@MODEL=$$($(PYTHON) -c "import yaml; d=yaml.safe_load(open('$(YAML)')); print(d.get('llm',{}).get('model','?'))" 2>/dev/null || echo '?') && \
		echo "  Modèle   : $$MODEL"
	@echo "  Service  : $$(systemctl is-active neron 2>/dev/null || echo 'inactif')"
	@echo ""

ollama:
	@$(SEP)
	@echo "  $(BOLD)$(BLUE)🦙 Gestion du modèle Ollama$(RESET)"
	@$(SEP)
	@echo ""
	@echo "  $(BOLD)Modèles installés :$(RESET)"
	@ollama list 2>/dev/null | tail -n +2 | awk '{print "  $(GREEN)•$(RESET) "$$1}' || $(call WARN,"aucun modèle installé")
	@echo ""
	@echo "  $(BOLD)Modèles recommandés :$(RESET)"
	@echo "  $(CYAN)•$(RESET) llama3.2:1b   — léger      (~1GB)"
	@echo "  $(CYAN)•$(RESET) llama3.2:3b   — équilibré  (~2GB)"
	@echo "  $(CYAN)•$(RESET) mistral       — performant (~4GB)"
	@echo "  $(CYAN)•$(RESET) gemma3        — Google     (~5GB)"
	@echo "  $(CYAN)•$(RESET) phi3          — Microsoft  (~2GB)"
	@echo ""
	@CURRENT=$$($(PYTHON) -c "import yaml; d=yaml.safe_load(open('$(YAML)')); print(d.get('llm',{}).get('model','llama3.2:1b'))" 2>/dev/null || echo 'llama3.2:1b') && \
		echo "  Modèle actuel : $(YELLOW)$$CURRENT$(RESET)" && \
		echo "" && \
		read -p "  Entrée = garder $$CURRENT, ou tapez un nouveau modèle : " MODEL && \
		MODEL=$${MODEL:-$$CURRENT} && \
		echo "" && \
		$(call STEP,"Téléchargement de $$MODEL...") && \
		if ollama pull $$MODEL; then \
			$(PYTHON) -c "\
import yaml; path='$(YAML)'; d=yaml.safe_load(open(path)); \
d.setdefault('llm',{})['model']='$$MODEL'; \
yaml.dump(d,open(path,'w'),allow_unicode=True,default_flow_style=False)"; \
			$(call OK,"neron.yaml mis à jour : llm.model=$$MODEL") && \
			echo "" && \
			read -p "  Redémarrer Néron maintenant ? [O/n] " RESTART && \
			[ "$$RESTART" != "n" ] && $(MAKE) -C $(BASE_DIR) restart || $(call WARN,"make restart quand vous êtes prêt"); \
		else \
			$(call FAIL,"Échec du téléchargement"); \
		fi

telegram:
	@bash $(BASE_DIR)/install.sh --telegram-only
