#!/bin/bash

ENV_FILE="/home/eleazar/Homebox_Neron/.env.global"

# Charge proprement le fichier .env
if [ -f "$ENV_FILE" ]; then
    set -o allexport
    source "$ENV_FILE"
    set +o allexport
else
    echo "Erreur : fichier .env.global introuvable !"
    exit 1
fi

# Vérification des variables Telegram
if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_CHAT_ID" ]; then
    echo "Erreur : BOT_TOKEN ou CHAT_ID manquant dans le .env"
    exit 1
fi

# Vérifie qu'on est dans un repo Git
if [ ! -d ".git" ]; then
    echo "Erreur : ce dossier n'est pas un dépôt Git."
    exit 1
fi

# Choix du type de commit
echo "Sélectionnez le type de commit :"
echo "1) feat     - nouvelle fonctionnalité"
echo "2) fix      - correction de bug"
echo "3) perf     - amélioration de performance"
echo "4) refactor - refactorisation"
echo "5) style    - formatage / style"
echo "6) docs     - documentation"
echo "7) test     - tests"
echo "8) build    - build / dépendances"
echo "9) ci       - CI/CD"
echo "10) chore   - tâches diverses"
read -p "Entrez le numéro correspondant : " TYPE_NUM

case $TYPE_NUM in
    1) PREFIX="feat" ;;
    2) PREFIX="fix" ;;
    3) PREFIX="perf" ;;
    4) PREFIX="refactor" ;;
    5) PREFIX="style" ;;
    6) PREFIX="docs" ;;
    7) PREFIX="test" ;;
    8) PREFIX="build" ;;
    9) PREFIX="ci" ;;
    10) PREFIX="chore" ;;
    *) echo "Erreur : choix invalide." ; exit 1 ;;
esac

# Demande le message du commit
read -p "Entrez le message du commit : " COMMIT_MSG

if [ -z "$COMMIT_MSG" ]; then
    echo "Erreur : message de commit vide."
    exit 1
fi

# Forme le message complet avec le préfixe
FULL_MSG="$PREFIX: $COMMIT_MSG"

# Ajout des fichiers
git add .

# Commit
git commit -m "$FULL_MSG"

# Push
git push -u origin main
if [ $? -ne 0 ]; then
    echo "Erreur : push échoué."
    exit 1
fi

# Envoi notification Telegram
curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d "chat_id=${TELEGRAM_CHAT_ID}" \
    -d text="🚀 *HomeBox* – Commit poussé avec succès :\n\n💬 $FULL_MSG" \
    -d parse_mode="Markdown" >/dev/null

echo "✅ Commit + push + notification Telegram envoyés !"

