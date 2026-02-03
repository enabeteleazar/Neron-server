#!/bin/bash
set -e

BASE_DIR="/opt/Neron_AI/neron-core"

echo "Création de l'arborescence minimale pour Néron Core..."

# -----------------------
# Core
# -----------------------
mkdir -p $BASE_DIR/core
cat > $BASE_DIR/core/__init__.py <<EOF
# Core package
EOF

cat > $BASE_DIR/core/config.py <<EOF
# Configuration minimale pour Néron
class Settings:
    ENV = "development"
    API_HOST = "127.0.0.1"
    API_PORT = 8000
    LOG_LEVEL = "INFO"

settings = Settings()
EOF

cat > $BASE_DIR/core/logging.py <<EOF
import logging

def init_logger(name="neron", level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        ch = logging.StreamHandler()
        ch.setLevel(level)
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(name)s: %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    return logger
EOF

cat > $BASE_DIR/core/bootstrap.py <<EOF
from core.config import settings
from core.logging import init_logger

logger = init_logger()

def main():
    logger.info(f"Bootstrapping Néron en {settings.ENV}")
    logger.info(f"API disponible sur {settings.API_HOST}:{settings.API_PORT}")
    logger.info(f"Niveau de log : {settings.LOG_LEVEL}")

if __name__ == "__main__":
    main()
EOF

# -----------------------
# Agents
# -----------------------
mkdir -p $BASE_DIR/agents
for f in __init__.py system_agent.py monitoring_agent.py; do
    cat > $BASE_DIR/agents/$f <<EOF
# $f minimal
EOF
done

# -----------------------
# Memory
# -----------------------
mkdir -p $BASE_DIR/memory
for f in __init__.py short_term.py long_term.py; do
    cat > $BASE_DIR/memory/$f <<EOF
# $f minimal
EOF
done

# -----------------------
# Orchestrator
# -----------------------
mkdir -p $BASE_DIR/orchestrator
for f in __init__.py orchestrator.py state.py; do
    cat > $BASE_DIR/orchestrator/$f <<EOF
# $f minimal
EOF
done

# -----------------------
# LLM
# -----------------------
mkdir -p $BASE_DIR/llm
for f in __init__.py client.py ollama_client.py models.py prompts.py; do
    cat > $BASE_DIR/llm/$f <<EOF
# $f minimal
EOF
done

# -----------------------
# Tools
# -----------------------
mkdir -p $BASE_DIR/tools/search
for f in __init__.py registry.py search.py; do
    if [ "$f" == "search.py" ]; then
        cat > $BASE_DIR/tools/search/$f <<EOF
# search.py minimal
EOF
    else
        cat > $BASE_DIR/tools/$f <<EOF
# $f minimal
EOF
    fi
done

echo "Tous les fichiers minimaux ont été créés !"
