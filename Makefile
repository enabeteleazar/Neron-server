# ============================================
# NÉRON AI — CLEAN MAKEFILE (v3)
# ============================================

REPO_DIR := /etc/neron
SERVER_DIR := $(REPO_DIR)/server
VENV_DIR := $(SERVER_DIR)/venv
PYTHON := $(VENV_DIR)/bin/python3
PIP := $(VENV_DIR)/bin/pip
SERVICE := neron

.PHONY: help install install-core install-systemd start stop restart status logs update clean test version telegram ha-config ollama install-client start-client backup restore neron

# ============================================
# HELP
# ============================================

help:
	@echo ""
	@echo "[Installation / Maintenance]"
	@echo "  make install    	-- installer Neron"
	@echo "  make update     	-- git pull + restart"
	@echo "  make clean      	-- nettoyer venv et logs"
	@echo "  make version    	-- versions Neron / Python / Ollama"
	@echo ""
	@echo "[Server]"
	@echo "  make start      	-- demarrer le service"
	@echo "  make stop       	-- arreter le service"
	@echo "  make restart    	-- redemarrer le service"
	@echo "  make status     	-- etat du service"
	@echo "  make logs       	-- logs en direct"
	@echo ""
	@echo "[Client]"
	@echo "  make start-client    	-- demarrer l'application"
	@echo "  make stop-client	-- arreter l'application "
	@echo "  make restart-client	-- relance l'application"
	@echo "  make status-client	-- etat de l'application"
	@echo "  make logs-client	-- logs en direct"
	@echo ""
	@echo "[Sauvegarde]"
	@echo "  make backup     	-- sauvegarder DB + neron.yaml"
	@echo "  make restore    	-- restaurer une sauvegarde"
	@echo ""
	@echo "[Diagnostic]"
	@echo "  make test       	-- tester l'API et Ollama"
	@echo "  make neron      	-- afficher la config active"
	@echo ""
	@echo "[Integration]"
	@echo "  make ollama     	-- gerer le modele Ollama"
	@echo "  make telegram   	-- configurer les bots Telegram"
	@echo ""
	@echo "[Home Assistant]"
	@echo "  make ha-start		-- Demarrer Home Assistant"
	@echo "  make ha-stop		-- Aretter Home Assistant "
	@echo "  make ha-restart   	-- Redemarrer Home Assistant"
	@echo "  make ha-install	-- installer Home Assistant"
	@echo "  make ha-config  	-- configurer Home Assistant"
	@echo ""

# ============================================
# INSTALL
# ============================================

install: install-core install-systemd
	@echo "✔ Installation terminée"

install-core:
	@echo "🔧 Install dépendances..."
	@sudo apt-get update -qq
	@sudo apt-get install -y -qq python3-venv git curl make

	@echo "🐍 Setup venv..."
	@test -d $(VENV_DIR) || python3 -m venv $(VENV_DIR)
	@$(PIP) install --upgrade pip -q

	@if [ -f $(SERVER_DIR)/requirements.txt ]; then \
		$(PIP) install -r $(SERVER_DIR)/requirements.txt -q; \
	fi

install-systemd:
	@echo "⚙️ systemd setup..."
	@printf '[Unit]\nDescription=Néron AI\nAfter=network.target\n\n[Service]\nType=simple\nWorkingDirectory=%s\nExecStart=%s %s/main.py\nRestart=always\nUser=root\nEnvironment=PYTHONUNBUFFERED=1\n\n[Install]\nWantedBy=multi-user.target\n' \
		"$(SERVER_DIR)" "$(PYTHON)" "$(SERVER_DIR)" \
		| sudo tee /etc/systemd/system/neron.service > /dev/null
	@sudo systemctl daemon-reload
	@sudo systemctl enable neron
	@echo "✔ systemd OK"

# ============================================
# SERVICE CONTROL
# ============================================

start:
	@sudo systemctl start $(SERVICE)

stop:
	@sudo systemctl stop $(SERVICE)

restart:
	@sudo systemctl restart $(SERVICE)

status:
	@systemctl status $(SERVICE) --no-pager

logs:
	@journalctl -u $(SERVICE) -f

# ============================================
# UPDATE
# ============================================

update:
	@echo "🔄 update..."
	@git -C $(SERVER_DIR) pull
	@$(PIP) install -r $(SERVER_DIR)/requirements.txt -q
	@sudo systemctl restart $(SERVICE)
	@echo "✔ updated"

# ============================================
# CLEAN
# ============================================

clean:
	@rm -rf $(VENV_DIR)
	@echo "✔ clean done"

# ============================================
# TEST
# ============================================

test:
	@bash $(SERVER_DIR)/scripts/test.sh

# ============================================
# VERSION
# ============================================

version:
	@echo "Python: $$(python3 --version)"
	@systemctl is-active $(SERVICE) > /dev/null 2>&1 && echo "Service: running" || echo "Service: stopped"

# ============================================
# CLIENT
# ============================================

start-client:
	@$(SERVER_DIR)/scripts/client.sh start

stop-client:
	@$(SERVER_DIR)/scripts/client.sh stop

restart-client:
	@$(SERVER_DIR)/scripts/client.sh restart

status-client:
	@$(SERVER_DIR)/scripts/client.sh status

logs-client:
	@$(SERVER_DIR)/scripts/client.sh logs

# ============================================
# BACKUP / RESTORE
# ============================================

backup:
	@bash $(SERVER_DIR)/scripts/backup.sh backup

restore:
	@bash $(SERVER_DIR)/scripts/backup.sh restore

# ============================================
# CONFIG DISPLAY
# ============================================

neron:
	@bash $(SERVER_DIR)/scripts/neron.sh

# ============================================
# EXTERNAL MODULES (CLEAN WRAPPERS)
# ============================================

telegram:
	@bash $(SERVER_DIR)/scripts/telegram.sh

ollama:
	@bash $(SERVER_DIR)/scripts/ollama.sh

# ============================================
# HOME ASSISTANT
# ============================================

# =========================
# HOME ASSISTANT
# =========================

ha-install:
	bash /etc/neron/server/scripts/ha_install.sh

ha-start:
	bash /etc/neron/server/scripts/ha.sh start

ha-stop:
	bash /etc/neron/server/scripts/ha.sh stop

ha-restart:
	bash /etc/neron/server/scripts/ha.sh restart

ha-status:
	bash /etc/neron/server/scripts/ha.sh status

ha-logs:
	bash /etc/neron/server/scripts/ha.sh logs

ha-config:
	bash /etc/neron/server/scripts/ha.sh config
