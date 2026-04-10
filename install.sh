#!/bin/bash
# install.sh - Néron AI v2.0 — YAML version (FIXED)

set -euo pipefail

# --- Couleurs ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

REPO_URL="https://github.com/enabeteleazar/Neron_AI.git"

# --- Install dir ---
INSTALL_DIR="${NERON_DIR:-/opt/neron}"

# --- Default branch ---
DEFAULT_BRANCH="release/v2.2.0"
BRANCH="${NERON_BRANCH:-$DEFAULT_BRANCH}"

# --- Validation branche remote ---
if command -v git >/dev/null 2>&1; then
    if ! git ls-remote --exit-code --heads "$REPO_URL" "$BRANCH" >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠ Branche '$BRANCH' invalide → fallback '$DEFAULT_BRANCH'${NC}"
        BRANCH="$DEFAULT_BRANCH"
    fi
fi

echo -e "${BLUE}➡ Branche utilisée : $BRANCH${NC}"

# --- Check OS ---
echo ""
echo -e "${BLUE}[1/7] Vérification système...${NC}"

if ! command -v apt-get >/dev/null 2>&1; then
    echo -e "${RED}❌ Ubuntu/Debian requis${NC}"
    exit 1
fi

# RAM
TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')
if [ "$TOTAL_RAM" -lt 2048 ]; then
    echo -e "${YELLOW}⚠ RAM faible : ${TOTAL_RAM}MB${NC}"
    read -p "Continuer ? [o/N] " CONTINUE
    [ "$CONTINUE" = "o" ] || exit 1
fi

# Disk
FREE_DISK=$(df -BG "$HOME" | awk 'NR==2{gsub("G",""); print $4}')
if [ "$FREE_DISK" -lt 10 ]; then
    echo -e "${YELLOW}⚠ Disque faible : ${FREE_DISK}GB${NC}"
    read -p "Continuer ? [o/N] " CONTINUE
    [ "$CONTINUE" = "o" ] || exit 1
fi

# --- Dependencies ---
echo ""
echo -e "${BLUE}[2/7] Dépendances...${NC}"

sudo apt-get update -qq

PYTHON_VENV_PKG="python3-venv"
python3 --version 2>/dev/null | grep -q "3.12" && PYTHON_VENV_PKG="python3.12-venv" || true

sudo apt-get install -y -qq \
    python3 \
    $PYTHON_VENV_PKG \
    python3-pip \
    git \
    make \
    curl \
    espeak \
    libespeak1 \
    ffmpeg \
    zstd \
    nano

echo -e "${GREEN}✔ OK${NC}"

# --- Ollama ---
echo ""
echo -e "${BLUE}[3/7] Ollama...${NC}"

if ! command -v ollama >/dev/null 2>&1; then
    curl -fsSL https://ollama.ai/install.sh | sh
fi

if ! systemctl is-active --quiet ollama 2>/dev/null; then
    if systemctl list-unit-files | grep -q ollama; then
        sudo systemctl enable ollama
        sudo systemctl start ollama
    else
        ollama serve &
    fi
fi

# --- Clone / Update ---
echo ""
echo -e "${BLUE}[4/7] Récupération Néron AI...${NC}"

if [ -d "$INSTALL_DIR/.git" ]; then
    echo -e "${YELLOW}⚠ Update repo...${NC}"
    git -C "$INSTALL_DIR" fetch origin
    git -C "$INSTALL_DIR" checkout "$BRANCH"
    git -C "$INSTALL_DIR" pull origin "$BRANCH"
else
    sudo mkdir -p "$(dirname "$INSTALL_DIR")"
    sudo rm -rf "$INSTALL_DIR"

    echo -e "${YELLOW}Clone: $REPO_URL ($BRANCH) → $INSTALL_DIR${NC}"

    sudo git clone --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR" || {
        echo -e "${YELLOW}⚠ Fallback develop${NC}"
        sudo git clone --branch "$DEFAULT_BRANCH" "$REPO_URL" "$INSTALL_DIR"
        BRANCH="$DEFAULT_BRANCH"
    }

    sudo chown -R "$(whoami):$(whoami)" "$INSTALL_DIR"
fi

# --- Check repo ---
if [ ! -f "$INSTALL_DIR/Makefile" ]; then
    echo -e "${RED}❌ Repo invalide${NC}"
    exit 1
fi

echo -e "${GREEN}✔ Repo OK${NC}"

# --- neron.yaml ---
echo ""
echo -e "${BLUE}[5/7] Configuration neron.yaml...${NC}"

if [ ! -f "$INSTALL_DIR/neron.yaml" ]; then
    if [ -f "$INSTALL_DIR/neron.example.yaml" ]; then
        cp "$INSTALL_DIR/neron.example.yaml" "$INSTALL_DIR/neron.yaml"
    else
        echo -e "${YELLOW}⚠ neron.yaml absent, création minimaliste${NC}"
        cat > "$INSTALL_DIR/neron.yaml" <<EOF
system:
  name: Néron
  version: 2.0
  install_dir: $INSTALL_DIR

llm:
  provider: ollama
  model: llama3

telegram:
  enabled: false
EOF
    fi
fi

echo -e "${GREEN}✔ neron.yaml prêt${NC}"

# --- Make install ---
echo ""
echo -e "${BLUE}[6/7] Installation...${NC}"

make -C "$INSTALL_DIR" install

# --- LLM model ---
echo ""
echo -e "${BLUE}[7/7] Modèle LLM...${NC}"

MODEL=$(grep -A2 "^llm:" "$INSTALL_DIR/neron.yaml" | grep "model:" | awk '{print $2}' || true)

if [ -n "$MODEL" ]; then
    if ollama list 2>/dev/null | grep -q "$MODEL"; then
        echo -e "${GREEN}✔ Modèle OK${NC}"
    else
        echo -e "${YELLOW}Téléchargement modèle $MODEL${NC}"
        ollama pull "$MODEL"
    fi
fi

# --- Summary ---
echo ""
echo -e "${BOLD}${GREEN}✔ Installation terminée${NC}"
echo ""
echo "Install dir : $INSTALL_DIR"
echo "Branch      : $BRANCH"
echo "Config      : neron.yaml"
echo ""
echo "Start : make -C $INSTALL_DIR start"
