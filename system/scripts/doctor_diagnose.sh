#!/usr/bin/env bash
# Diagnostic periodique de doctor — declenche par neron-doctor-diagnose.timer
set -euo pipefail

SECRETS_FILE="/etc/neronOS/secrets.env"
DOCTOR_URL="http://127.0.1.9:8060/diagnose"

if [ -f "$SECRETS_FILE" ]; then
    # shellcheck disable=SC1090
    source <(grep -E '^NERON_DOCTOR_API_KEY=' "$SECRETS_FILE")
fi

if [ -z "${NERON_DOCTOR_API_KEY:-}" ]; then
    echo "NERON_DOCTOR_API_KEY absente — diagnostic annule" >&2
    exit 1
fi

response=$(curl -sS -w '\n%{http_code}' -X POST \
    -H "X-Doctor-Key: ${NERON_DOCTOR_API_KEY}" \
    "$DOCTOR_URL")

status_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

echo "Diagnostic doctor — code HTTP ${status_code}"
echo "$body"

if [ "$status_code" != "200" ]; then
    exit 1
fi
