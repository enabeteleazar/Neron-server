# ===================wsystem=========================
# Néron AI v2.1 — Makefile propre
# ============================================

BASE_DIR   := /etc/neron
REPO_DIR   := $(BASE_DIR)/server
VENV_DIR   := $(BASE_DIR)/server/venv
PYTHON     := $(VENV_DIR)/bin/python3
PIP        := $(VENV_DIR)/bin/pip
SERVICE    := neron
LOG_DIR    := $(BASE_DIR)/logs
SYSTEMD    := /etc/systemd/system/neron.service

.PHONY: install install-core install-systemd start stop restart status logs update clean backup restore test version neron ollama telegram ha-agent help install-client start-client

# ============================================
# HELP
# ============================================

help:
	@echo ""
	@echo "Néron AI - commandes disponibles"
	@echo ""
	@echo "  make install        installation complète"
	@echo "  make update         mise à jour safe"
	@echo "  make start          démarrer"
	@echo "  make stop           arrêter"
	@echo "  make restart        redémarrer"
	@echo "  make status         état"
	@echo "  make logs           logs systemd"
	@echo "  make clean          reset venv"
	@echo ""
	@echo "  make backup         backup config"
	@echo "  make restore        restore backup"
	@echo "  make version        versions"
	@echo "  make test           test API"
	@echo ""

# ============================================
# INSTALLATION
# ============================================

install: install-core install-systemd
	@echo ""
	@echo "✔ Installation terminée"
	@echo "👉 Config : nano $(REPO_DIR)/neron.yaml"
	@echo "👉 Start  : make start"

install-core:
	@echo "🔧 Installation Néron AI..."
	@sudo apt-get update -qq
	@sudo apt-get install -y -qq \
		espeak ffmpeg git curl nano make python3-venv

	@echo "🐍 Setup Python venv..."
	@test -d $(VENV_DIR) || python3 -m venv $(VENV_DIR)
	@$(PIP) install --upgrade pip -q
	@if [ -f $(REPO_DIR)/requirements.txt ]; then \
		$(PIP) install -r $(REPO_DIR)/requirements.txt -q; \
	fi

	@mkdir -p $(LOG_DIR)

install-systemd:
	@echo "⚙️  Installation systemd..."

	@if [ ! -f $(SYSTEMD) ]; then \
		echo "❌ SYSTEMD systemd manquant: $(SYSTEMD)"; \
		exit 1; \
	fi

	@sed -e "s|__NERON_DIR__|$(BASE_DIR)|g" \
		-e "s|__NERON_USER__|$(shell whoami)|g" \
		$(SYSTEMD) > /tmp/neron.service

	@sudo cp /tmp/neron.service $(SYSTEMD)
	@rm -f /tmp/neron.service

	@sudo systemctl daemon-reload
	@sudo systemctl enable $(SERVICE)

	@echo "✔ systemd OK"

# ============================================
# CONTROL SERVICE
# ============================================

start:
	@sudo systemctl start $(SERVICE)
	@sleep 2
	@sudo systemctl is-active --quiet $(SERVICE) && echo "✔ running" || (echo "❌ error" && exit 1)

stop:
	@sudo systemctl stop $(SERVICE)
	@echo "✔ stopped"

restart:
	@sudo systemctl restart $(SERVICE)
	@sleep 2
	@sudo systemctl is-active --quiet $(SERVICE) && echo "✔ restarted" || (echo "❌ error" && exit 1)

status:
	@sudo systemctl status $(SERVICE) --no-pager

logs:
	@sudo journalctl -u $(SERVICE) -f

# ============================================
# UPDATE SAFE
# ============================================

update:
	@echo "🔄 update Néron..."
	@git -C $(REPO_DIR) pull origin $$(git -C $(REPO_DIR) branch --show-current)
	@$(PIP) install -r $(BASE_DIR)/requirements.txt -q
	@sudo systemctl restart $(SERVICE)
	@echo "✔ updated"

# ============================================
# CLEAN
# ============================================

clean:
	@echo "🧹 reset venv..."
	@rm -rf $(VENV_DIR)
	@rm -f $(LOG_DIR)/*.log
	@echo "✔ clean done"

# ============================================
# BACKUP
# ============================================

backup:
	@echo "💾 backup..."
	@DIR=$(BASE_DIR)/backups/$$(date +%Y%m%d_%H%M%S) && \
	mkdir -p $$DIR && \
	cp $(BASE_DIR)/neron.yaml $$DIR/ 2>/dev/null || true && \
	cp -r $(BASE_DIR)/data $$DIR/ 2>/dev/null || true && \
	echo "✔ backup: $$DIR"

restore:
	@echo "📂 restore..."
	@ls -lt $(BASE_DIR)/backups/ | head -n 10
	@read -p "folder: " F && \
	cp -r $(BASE_DIR)/backups/$$F/* $(BASE_DIR)/

# ============================================
# TEST
# ============================================

test:
	@curl -sf http://localhost:8010/health && echo "✔ API OK" || echo "❌ API KO"
	@curl -sf http://localhost:11434/api/tags && echo "✔ Ollama OK" || echo "❌ Ollama KO"

# ============================================
# VERSION
# ============================================

version:
	@echo ""
	@echo "Néron AI"
	@echo "Python : $$(python3 --version)"
	@echo "Service: $$(systemctl is-active neron 2>/dev/null || echo 'inactive')"
	@echo ""

# ============================================
# CLIENT
# ============================================

install-client:
	@cd ../client && npm install

start-client:
	@cd ../client && npm run dev

# ============================================
# OLLAMA / HA / TELEGRAM (hooks externes)
# ============================================

ollama:
	@bash $(REPO_DIR)/scripts/ollama.sh

telegram:
	@bash $(REPO_DIR)/scripts/telegram.sh

ha-agent:
	@bash $(REPO_DIR)/scripts/ha.sh
