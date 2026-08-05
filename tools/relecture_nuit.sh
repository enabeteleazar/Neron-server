#!/usr/bin/env bash
# Relecture nocturne de la memoire : rejoue l extraction sur d anciens
# messages bruts pour corroborer les fiches du brouillon.
# Calibrage : ~400 s par message sur Homebox, donc 9 messages ~= 1 h.
set -euo pipefail
: "${NERON_API_KEY:?NERON_API_KEY absente}"
curl -sS --max-time 4200 -X POST http://127.0.1.4:8040/memory/reread \
  -H "Authorization: Bearer ${NERON_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"limit":9}'
echo
