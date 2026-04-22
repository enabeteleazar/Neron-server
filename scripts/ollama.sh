#!/usr/bin/env bash
# scripts/ollama.sh

set -e
clear

# =========================
# COLORS
# =========================
BOLD="\033[1m"
BLUE="\033[34m"
YELLOW="\033[33m"
GREEN="\033[32m"
NC="\033[0m"


# =========================
# UI FUNCTIONS
# =========================
slow_echo() {
    local text="$1"
    local delay="${2:-0.02}"
    for ((i=0; i<${#text}; i++)); do
        printf "%s" "${text:$i:1}"
        sleep $delay
    done
    echo
}

spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='|/-\\'
    while ps -p "$pid" > /dev/null 2>&1; do
        local temp=${spinstr#?}
        printf " [%c]  " "${spinstr}"
        spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "      \b\b\b\b\b\b"
}

echo ""
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  📱 Configuration Ollama + Model Manager"
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

BASE_DIR="/etc/neron/server"
INSTALL_DIR="$BASE_DIR"
LLMFIT="$BASE_DIR/scripts/llmfit/llmfit.py"
CONFIG_FILE="$INSTALL_DIR/neron.yaml"

# ------------------------------------------------------
# [1/5] OLLAMA INSTALLATION
# ------------------------------------------------------
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[1/5] Vérification Ollama...${NC}"

if ! command -v ollama >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠ Ollama non trouvé — installation...${NC}"
    curl -fsSL https://ollama.ai/install.sh | sh
    echo -e "${GREEN}✔ Ollama installé${NC}"
else
    VERSION=$(ollama --version 2>/dev/null || echo "version inconnue")
    echo -e "${GREEN}✔ Ollama OK (${VERSION})${NC}"
fi

# ------------------------------------------------------
# [2/5] SERVICE OLLAMA
# ------------------------------------------------------
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[2/5] Vérification du service...${NC}"

if systemctl is-active --quiet ollama 2>/dev/null; then
    echo -e "${GREEN}✔ Ollama déjà actif${NC}"
else
    if systemctl list-unit-files | grep -q ollama; then
        sudo systemctl enable ollama
        sudo systemctl start ollama
        echo -e "${GREEN}✔ Service Ollama démarré (systemd)${NC}"
    else
        echo -e "${YELLOW}⚠ Mode sans systemd → lancement manuel${NC}"
        ollama serve >/dev/null 2>&1 &
        sleep 2
        echo -e "${GREEN}✔ Service Ollama démarré${NC}"
    fi
fi

# ------------------------------------------------------
# [3/5] LLMFIT + RECOMMANDATIONS
# ------------------------------------------------------
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[3/5] Analyse hardware + recommandations...${NC}"
echo ""

RAW_OUTPUT=""

if [ -f "$LLMFIT" ]; then
    RAW_OUTPUT=$(python3 "$LLMFIT" recommend --limit 5 2>/dev/null || echo "")
fi

if [ -z "$RAW_OUTPUT" ]; then
    echo -e "${YELLOW}⚠ llmfit indisponible${NC}"
else
    python3 - <<EOF
import json

data = json.loads("""$RAW_OUTPUT""")
s = data["system"]
models = data["models"]

print("  💻 Hardware détecté :")
print(f"     CPU     : {s['cpu']}")
print(f"     RAM     : {s['ram_gb']} GB disponible")
print(f"     GPU     : {s['gpu'] or 'aucun'}")
print(f"     Backend : {s['backend']}")
print()
print("  🏆 Modèles recommandés :")

icons = {"Perfect": "🟢", "Good": "🟡", "Marginal": "🟠"}

for i, m in enumerate(models):
    name = m["name"].split("/")[-1]
    print(f"     {i+1}. {icons.get(m['fit'],'🔴')} {name:<45} score:{m['score']:>5}")
EOF
fi

# ------------------------------------------------------
# 🔥 MODEL MAPPING (CRUCIAL FIX)
# ------------------------------------------------------
declare -A MODEL_MAP=(
    ["Phi-mini-MoE-instruct"]="phi3:mini"
    ["Phi-tiny-MoE-instruct"]="phi3:mini"
    ["OLMoE-1B-7B-0125-Instruct"]="mistral:7b"
    ["OLMoE-1B-7B-0125"]="mistral:7b"
    ["LFM2-8B-A1B"]="llama3:8b"
)

# ------------------------------------------------------
# [4/5] CHOIX DU MODELE
# ------------------------------------------------------
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[4/5] Sélection du modèle...${NC}"

if [ -z "$RAW_OUTPUT" ]; then
    echo -e "${YELLOW}⚠ Aucun modèle disponible${NC}"
    exit 0
fi

BEST_MODEL=$(python3 - <<EOF
import json
data = json.loads("""$RAW_OUTPUT""")
print(data["models"][0]["name"].split("/")[-1])
EOF
)

echo ""
echo "🤖 Modèle recommandé : $BEST_MODEL"
read -p "Appliquer automatiquement ce modèle ? [O/n] " APPLY

if [ "$APPLY" != "n" ]; then
    SELECTED_MODEL="$BEST_MODEL"
else
    echo ""
    echo "📋 Modèles disponibles :"

    python3 - <<EOF
import json
data = json.loads("""$RAW_OUTPUT""")
for i, m in enumerate(data["models"]):
    print(f"{i+1}. {m['name'].split('/')[-1]}")
EOF

    echo ""
    echo "0. ➕ Entrer un modèle personnalisé"
    echo ""

    read -p "Choisir un modèle (1-5 / 0) : " IDX

    if [ "$IDX" = "0" ]; then
        read -p "Nom du modèle Ollama personnalisé : " SELECTED_MODEL
    else
        SELECTED_MODEL=$(python3 - <<EOF
import json
data = json.loads("""$RAW_OUTPUT""")
i = int("$IDX") - 1
print(data["models"][i]["name"].split("/")[-1])
EOF
)
    fi
fi

echo ""
echo "✔ Modèle sélectionné : $SELECTED_MODEL"

# ------------------------------------------------------
# 🔄 MAPPING VERS OLLAMA
# ------------------------------------------------------
OLLAMA_MODEL="${MODEL_MAP[$SELECTED_MODEL]:-$SELECTED_MODEL}"

echo ""
echo "🔄 Mapping modèle : $SELECTED_MODEL → $OLLAMA_MODEL"

# ------------------------------------------------------
# [5/5] YAML UPDATE + SAFE PULL
# ------------------------------------------------------
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[5/5] Mise à jour configuration...${NC}"

if [ -f "$CONFIG_FILE" ]; then

python3 - <<EOF
import yaml

file = "$CONFIG_FILE"

with open(file) as f:
    data = yaml.safe_load(f)

data.setdefault("llm", {})
data["llm"]["model"] = "$OLLAMA_MODEL"

with open(file, "w") as f:
    yaml.dump(data, f, sort_keys=False)

print("✔ neron.yaml mis à jour")
EOF

else
    echo -e "${YELLOW}⚠ neron.yaml introuvable${NC}"
fi

echo ""
echo "📥 Vérification modèle Ollama..."

if ollama list 2>/dev/null | grep -q "$OLLAMA_MODEL"; then
    echo "✔ Modèle déjà présent"
else
    echo "⬇ Téléchargement du modèle Ollama..."

    if ! ollama pull "$OLLAMA_MODEL"; then
        echo ""
        echo "❌ Erreur: modèle introuvable dans registry Ollama"
        echo "👉 Vérifie avec : ollama search $OLLAMA_MODEL"
        exit 1
    fi

    echo "✔ Modèle installé"
fi

# ------------------------------------------------------
# RESTART OPTION
# ------------------------------------------------------
echo ""
echo -e "${GREEN}✔ Setup Ollama complet terminé${NC}"
echo ""

read -p "🔁 Redémarrer Ollama pour appliquer les changements ? [O/n] " RESTART

if [ "$RESTART" != "n" ]; then
    echo ""
    echo "🔄 Redémarrage Ollama..."

    if systemctl is-active --quiet ollama 2>/dev/null; then
        sudo systemctl restart ollama
    else
        pkill ollama || true
        nohup ollama serve >/dev/null 2>&1 &
    fi

    echo "✔ Ollama redémarré"
else
    echo "👉 Redémarrage ignoré"
fi

echo ""
