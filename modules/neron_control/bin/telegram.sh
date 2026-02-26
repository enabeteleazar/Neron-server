#!/bin/bash

# Charger Telegram depuis /opt/Homebox_AI/.env
if [ -f /opt/Homebox_AI/.env ]; then
    export $(grep -v '^#' /opt/Homebox_AI/.env | xargs)
fi

MESSAGE="$1"

if [[ -n "$TELEGRAM_BOT_TOKEN" && -n "$TELEGRAM_CHAT_ID" ]]; then
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
         -d chat_id="${TELEGRAM_CHAT_ID}" \
         -d text="HOMEBOX: ${MESSAGE}" \
         > /dev/null
fi
