#!/bin/bash

echo "🧠 Initialisation de l’arborescence Néron..."

# Racine
mkdir -p neron
cd neron || exit 1

# Fichiers racine
touch README.md run.py

# =========================
# neron-core (cerveau)
# =========================
mkdir -p neron-core
touch neron-core/main.py
touch neron-core/orchestrator.py
touch neron-core/router.py
touch neron-core/state.py
touch neron-core/README.md

# =========================
# neron-llm (LLM)
# =========================
mkdir -p neron-llm
touch neron-llm/client.py
touch neron-llm/models.py
touch neron-llm/prompt.py
touch neron-llm/README.md

# =========================
# neron-io (entrées / sorties)
# =========================
mkdir -p neron-io/telegram
mkdir -p neron-io/api
mkdir -p neron-io/cli
touch neron-io/telegram/bot.py
touch neron-io/api/server.py
touch neron-io/cli/cli.py
touch neron-io/README.md

# =========================
# neron-memory (mémoire)
# =========================
mkdir -p neron-memory
touch neron-memory/short_term.py
touch neron-memory/long_term.py
touch neron-memory/vector.py
touch neron-memory/README.md

# =========================
# neron-agent (agents)
# =========================
mkdir -p neron-agent
touch neron-agent/base_agent.py
touch neron-agent/planner_agent.py
touch neron-agent/README.md

# =========================
# neron-bridge (interconnexion)
# =========================
mkdir -p neron-bridge
touch neron-bridge/message_bus.py
touch neron-bridge/contracts.py
touch neron-bridge/README.md

# =========================
# Modèles communs
# =========================
mkdir -p models
touch models/message.py
touch models/intent.py
touch models/response.py

# =========================
# Config
# =========================
mkdir -p config
touch config/settings.py

# =========================
# Utils
# =========================
mkdir -p utils
touch utils/logger.py

echo "✅ Arborescence Néron créée avec succès"
