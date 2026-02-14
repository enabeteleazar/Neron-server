#!/bin/bash
# modules/neron_llm/init_models.sh

"""
Script pour initialiser les modèles Ollama
Usage: ./init_models.sh [model_name]
"""

set -e

OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
DEFAULT_MODELS=("llama3.2:1b" "mistral:latest")

echo "🚀 Initialisation des modèles Ollama"
echo "Host: $OLLAMA_HOST"
echo ""

# Fonction pour vérifier la connexion
check_ollama() {
    echo "🔍 Vérification de la connexion à Ollama..."
    if curl -s -f "$OLLAMA_HOST/api/tags" > /dev/null 2>&1; then
        echo "✅ Connexion établie"
        return 0
    else
        echo "❌ Impossible de se connecter à Ollama"
        return 1
    fi
}

# Fonction pour télécharger un modèle
pull_model() {
    local model=$1
    echo ""
    echo "📥 Téléchargement du modèle: $model"
    
    if ollama pull "$model"; then
        echo "✅ Modèle $model téléchargé"
    else
        echo "❌ Erreur lors du téléchargement de $model"
        return 1
    fi
}

# Fonction pour lister les modèles
list_models() {
    echo ""
    echo "📋 Modèles installés:"
    ollama list
}

# Vérifier la connexion
if ! check_ollama; then
    echo ""
    echo "⚠️  Assurez-vous qu'Ollama est en cours d'exécution:"
    echo "   docker-compose up -d neron-ollama"
    exit 1
fi

# Si un modèle est spécifié, le télécharger
if [ $# -gt 0 ]; then
    pull_model "$1"
else
    # Sinon, télécharger les modèles par défaut
    echo "📦 Téléchargement des modèles par défaut..."
    for model in "${DEFAULT_MODELS[@]}"; do
        pull_model "$model"
    done
fi

# Lister les modèles installés
list_models

echo ""
echo "🎉 Initialisation terminée!"
