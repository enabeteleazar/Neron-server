#!/bin/bash

# Charger les variables .env
export $(grep -v '^#' .env | xargs)

# Configurer Git
git config user.name "$GIT_USER"
git config user.email "$GIT_EMAIL"

while true; do
    # Vérifier les changements
    if git diff-index --quiet HEAD --; then
        echo "$(date) - Aucun changement détecté."
    else
        # Commit automatique
        COMMIT_MSG="Automated commit: $(date '+%Y-%m-%d %H:%M:%S')"
        git add .
        git commit -m "$COMMIT_MSG"
        git push "$REPO_URL" "$BRANCH"

        # Lien vers le commit
        COMMIT_HASH=$(git rev-parse HEAD)
        COMMIT_LINK="${REPO_URL%.git}/commit/$COMMIT_HASH"

        # Notification Telegram via Python
        python3 telegram_send.py "$COMMIT_MSG" "$COMMIT_LINK"
    fi

    # Attendre l'intervalle avant de vérifier à nouveau
    sleep ${PUSH_INTERVAL:-300}
done
