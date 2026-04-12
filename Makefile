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
	@echo ""
	@echo "[Client]"
	@echo "  make client-start    	-- demarrer l'application"
	@echo "  make client-stop	-- arreter l'application "
	@echo "  make client-restart	-- relance l'application"
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
	@bash $(SERVER_DIR)/scripts/version.sh

# ============================================
# CLIENT
# ============================================

client-start:
	@bash $(SERVER_DIR)/scripts/client.sh start

client-stop:
	@bash $(SERVER_DIR)/scripts/client.sh stop

client-restart:
	@bash $(SERVER_DIR)/scripts/client.sh restart


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

ha-install:
	@bash $(SERVER_DIR)/scripts/ha_install.sh

ha-start:
	@bash $(SERVER_DIR)/scripts/ha.sh start

ha-stop:
	@bash $(SERVER_DIR)/scripts/ha.sh stop

ha-restart:
	@bash $(SERVER_DIR)/scripts/ha.sh restart

ha-status:
	@bash $(SERVER_DIR)/scripts/ha.sh status

ha-logs:
	@bash $(SERVER_DIR)/scripts/ha.sh logs

ha-config:
	@bash $(SERVER_DIR)/scripts/ha.sh config
