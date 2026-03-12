# ============================================
#  Neron AI v2.1 -- Makefile
# ============================================

BASE_DIR  := /mnt/usb-storage/neron/server
VENV      := $(BASE_DIR)/venv
PYTHON    := $(VENV)/bin/python3
PIP       := $(VENV)/bin/pip
SERVICE   := neron
LOG_DIR   := /mnt/usb-storage/neron/data/logs
DATA_DIR  := /mnt/usb-storage/neron/data
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
OK    = echo "  $(GREEN)$(BOLD)OK$(RESET) $(1)"
FAIL  = echo "  $(RED)$(BOLD)FAIL$(RESET) $(1)" && exit 1
WARN  = echo "  $(YELLOW)WARN$(RESET)  $(1)"
STEP  = echo "$(BLUE)$(BOLD)>>$(RESET) $(1)"
SEP   = echo "$(CYAN)$(BOLD)----------------------------------------$(RESET)"

.PHONY: install start stop restart status logs update help clean backup restore test ollama telegram env version

all: help

help:
	@$(SEP)
	@echo "  $(BOLD)$(BLUE)Neron AI v2.1 -- Commandes$(RESET)"
	@$(SEP)
	@echo ""
	@echo "  $(BOLD)make install$(RESET)    -- installer Neron"
	@echo "  $(BOLD)make start$(RESET)      -- demarrer le service"
	@echo "  $(BOLD)make stop$(RESET)       -- arreter le service"
	@echo "  $(BOLD)make restart$(RESET)    -- redemarrer le service"
	@echo "  $(BOLD)make status$(RESET)     -- etat du service"
	@echo "  $(BOLD)make logs$(RESET)       -- logs en direct"
	@echo "  $(BOLD)make update$(RESET)     -- git pull + restart"
	@echo "  $(BOLD)make clean$(RESET)      -- nettoyer venv et logs"
	@echo "  $(BOLD)make backup$(RESET)     -- sauvegarder DB + neron.yaml"
	@echo "  $(BOLD)make restore$(RESET)    -- restaurer une sauvegarde"
	@echo "  $(BOLD)make test$(RESET)       -- tester l'API et Ollama"
	@echo "  $(BOLD)make ollama$(RESET)     -- gerer le modele Ollama"
	@echo "  $(BOLD)make telegram$(RESET)   -- configurer les bots Telegram"
	@echo "  $(BOLD)make env$(RESET)        -- afficher la config active"
	@echo "  $(BOLD)make version$(RESET)    -- versions Neron / Python / Ollama"
	@echo ""

install:
	@$(SEP)
	@echo "  $(BOLD)$(BLUE)Installation de Neron AI$(RESET)"
	@$(SEP)
	@$(call STEP,"Dependances systeme...")
	@sudo apt-get update -qq > /dev/null 2>&1
	@sudo apt-get install -y -qq espeak libespeak1 ffmpeg git curl tree nano make python3-yaml > /dev/null 2>&1
	@$(call OK,"Dependances systeme OK")
	@$(call STEP,"Creation du venv Python...")
	@test -d $(VENV) || python3 -m venv $(VENV)
	@$(PIP) install --upgrade pip -q > /dev/null 2>&1
	@$(PIP) install -r $(BASE_DIR)/requirements.txt -q > /dev/null 2>&1
	@$(call OK,"Venv Python OK")
	@mkdir -p $(LOG_DIR) $(DATA_DIR)/models
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
	@$(call OK,"Service systemd active")
	@echo ""
	@$(SEP)
	@echo "  $(GREEN)$(BOLD)Installation terminee !$(RESET)"
	@$(SEP)
	@echo "  $(BOLD)1.$(RESET) Configurez : $(YELLOW)nano $(YAML)$(RESET)"
	@echo "  $(BOLD)2.$(RESET) Lancez     : $(YELLOW)make start$(RESET)"

start:
	@$(call STEP,"Arret eventuel sur le port 8000...")
	@sudo fuser -k 8000/tcp 2>/dev/null || true
	@$(call STEP,"Demarrage de Neron...")
	@sudo systemctl start $(SERVICE)
	@sleep 2
	@if sudo systemctl is-active --quiet $(SERVICE); then \
		echo "  OK Neron demarre"; \
	else \
		echo "  FAIL Echec -- make logs pour plus d infos"; exit 1; \
	fi

stop:
	@$(call STEP,"Arret de Neron...")
	@sudo systemctl stop $(SERVICE)
	@$(call OK,"Neron arrete")

restart:
	@$(call STEP,"Redemarrage de Neron...")
	@sudo fuser -k 8000/tcp 2>/dev/null || true
	@sudo systemctl restart $(SERVICE)
	@sleep 2
	@if sudo systemctl is-active --quiet $(SERVICE); then \
		echo "  OK Neron redemarre"; \
	else \
		echo "  FAIL Echec -- make logs pour plus d infos"; exit 1; \
	fi

status:
	@echo ""
	@$(SEP)
	@echo "  $(BOLD)$(BLUE)Statut du service$(RESET)"
	@$(SEP)
	@sudo systemctl status $(SERVICE) --no-pager

logs:
	@echo "  $(CYAN)Logs en direct -- Ctrl+C pour quitter$(RESET)"
	@echo ""
	@sudo journalctl -u $(SERVICE) -f

update:
	@$(call STEP,"Mise a jour de Neron...")
	@git -C $(BASE_DIR) pull origin master > /dev/null 2>&1
	@$(call OK,"Code mis a jour")
	@$(PIP) install -r $(BASE_DIR)/requirements.txt -q > /dev/null 2>&1
	@$(call OK,"Dependances mises a jour")
	@sudo systemctl restart $(SERVICE)
	@sleep 2
	@if sudo systemctl is-active --quiet $(SERVICE); then \
		echo "  OK Neron redemarre"; \
	else \
		echo "  WARN Echec au redemarrage"; \
	fi

clean:
	@$(call STEP,"Nettoyage...")
	@read -p "  Supprimer le venv et les logs ? [o/N] " confirm && \
		[ "$$confirm" = "o" ] || exit 0
	@rm -rf $(VENV)
	@rm -f $(LOG_DIR)/*.log
	@$(call OK,"Nettoyage termine")

backup:
	@$(call STEP,"Sauvegarde de Neron...")
	@BACKUP_DIR=$(BASE_DIR)/backups/$$(date +%Y%m%d_%H%M%S) && \
		mkdir -p $$BACKUP_DIR && \
		cp $(YAML) $$BACKUP_DIR/neron.yaml && \
		cp $(DATA_DIR)/memory.db $$BACKUP_DIR/memory.db 2>/dev/null || true && \
		echo "  OK Sauvegarde creee : $$BACKUP_DIR"

restore:
	@$(call STEP,"Restauration...")
	@echo "  $(BOLD)Sauvegardes disponibles :$(RESET)"
	@ls -lt $(BASE_DIR)/backups/ 2>/dev/null | grep "^d" | awk '{print "  "$$NF}' || \
		echo "  WARN Aucune sauvegarde trouvee"
	@echo ""
	@read -p "  Nom du dossier a restaurer : " BACKUP && \
		test -d $(BASE_DIR)/backups/$$BACKUP && \
		cp $(BASE_DIR)/backups/$$BACKUP/neron.yaml $(YAML) && \
		cp $(BASE_DIR)/backups/$$BACKUP/memory.db $(DATA_DIR)/memory.db 2>/dev/null || true && \
		echo "  OK Restauration terminee -- make restart pour appliquer"

test:
	@$(SEP)
	@echo "  $(BOLD)$(BLUE)Test de l API Neron$(RESET)"
	@$(SEP)
	@echo ""
	@if curl -sf http://localhost:8000/health > /dev/null; then \
		echo "  OK Core API repond (port 8000)"; \
	else \
		echo "  WARN Core API ne repond pas"; \
	fi
	@if curl -sf http://localhost:11434/api/tags > /dev/null; then \
		echo "  OK Ollama repond"; \
	else \
		echo "  WARN Ollama ne repond pas"; \
	fi
	@echo ""

env:
	@$(SEP)
	@echo "  $(BOLD)$(BLUE)Configuration active$(RESET) $(YELLOW)(tokens masques)$(RESET)"
	@$(SEP)
	@echo ""
	@$(PYTHON) -c "\
import yaml; \
d = yaml.safe_load(open('$(YAML)')); \
sections = ['neron','server','llm','stt','tts','memory','watchdog']; \
[print('  [' + s + ']') or \
 [print('    ' + k + ': ' + ('****' if any(x in k for x in ['token','key','secret']) else str(v))) \
  for k,v in d.get(s,{}).items()] \
 for s in sections if s in d]" 2>/dev/null
	@echo ""

version:
	@$(SEP)
	@echo "  $(BOLD)$(BLUE)Neron AI -- Versions$(RESET)"
	@$(SEP)
	@echo ""
	@grep -m1 "^VERSION" $(BASE_DIR)/core/app.py 2>/dev/null | \
		cut -d'"' -f2 | awk '{print "  Version  : "$$1}' || echo "  Version  : inconnue"
	@echo "  Python   : $$(python3 --version 2>&1 | cut -d' ' -f2)"
	@echo "  Ollama   : $$(ollama --version 2>/dev/null || echo non-trouve)"
	@MODEL=$$($(PYTHON) -c "import yaml; d=yaml.safe_load(open('$(YAML)')); print(d.get('llm',{}).get('model','?'))" 2>/dev/null || echo '?') && \
		echo "  Modele   : $$MODEL"
	@echo "  Service  : $$(systemctl is-active neron 2>/dev/null || echo inactif)"
	@echo ""

ollama:
	@$(SEP)
	@echo "  $(BOLD)$(BLUE)Gestion du modele Ollama$(RESET)"
	@$(SEP)
	@echo ""
	@echo "  $(BOLD)Modeles installes :$(RESET)"
	@ollama list 2>/dev/null | tail -n +2 | awk '{print "  * "$$1}' || echo "  WARN aucun modele installe"
	@echo ""
	@echo "  $(BOLD)Modeles recommandes :$(RESET)"
	@echo "  * llama3.2:1b   -- leger      (~1GB)"
	@echo "  * llama3.2:3b   -- equilibre  (~2GB)"
	@echo "  * mistral       -- performant (~4GB)"
	@echo "  * gemma3        -- Google     (~5GB)"
	@echo "  * phi3          -- Microsoft  (~2GB)"
	@echo ""
	@CURRENT=$$($(PYTHON) -c "import yaml; d=yaml.safe_load(open('$(YAML)')); print(d.get('llm',{}).get('model','llama3.2:1b'))" 2>/dev/null || echo 'llama3.2:1b') && \
		echo "  Modele actuel : $$CURRENT" && \
		echo "" && \
		read -p "  Entree = garder $$CURRENT, ou tapez un nouveau modele : " MODEL && \
		MODEL=$${MODEL:-$$CURRENT} && \
		echo "" && \
		if ollama pull $$MODEL; then \
			$(PYTHON) -c "import yaml; path='$(YAML)'; d=yaml.safe_load(open(path)); d.setdefault('llm',{})['model']='$$MODEL'; yaml.dump(d,open(path,'w'),allow_unicode=True,default_flow_style=False)"; \
			echo "  OK neron.yaml mis a jour : llm.model=$$MODEL" && \
			echo "" && \
			read -p "  Redemarrer Neron maintenant ? [O/n] " RESTART && \
			[ "$$RESTART" != "n" ] && $(MAKE) -C $(BASE_DIR) restart || echo "  WARN make restart quand vous etes pret"; \
		else \
			echo "  FAIL Echec du telechargement"; exit 1; \
		fi

telegram:
	@bash $(BASE_DIR)/install.sh --telegram-only
