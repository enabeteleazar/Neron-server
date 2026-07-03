#!/usr/bin/env bash
set -euo pipefail

ROLE="${1:-}"

cd /etc/neron

set -a
[ -f /etc/neron/secrets.env ] && source /etc/neron/secrets.env
[ -f /etc/neron/system/config/network.env ] && source /etc/neron/system/config/network.env
set +a

source /etc/neron/venv/bin/activate

case "$ROLE" in
  core)
    export PYTHONPATH=/etc/neron/server:/etc/neron/server/llm
    exec python -m uvicorn core.app:app --host "${NERON_CORE_HOST:-0.0.0.0}" --port "${NERON_CORE_PORT:-8010}"
    ;;
  llm)
    export PYTHONPATH=/etc/neron/server:/etc/neron/server/llm
    exec python -m uvicorn llm.app:app --host "${NERON_LLM_HOST:-0.0.0.0}" --port "${NERON_LLM_PORT:-8765}"
    ;;
  memory)
    export PYTHONPATH=/etc/neron/server
    export NERON_SERVICE_HOST="${NERON_SERVICE_HOST:-u4-neron-memory}"
    export NERON_SERVICE_PORT="${NERON_SERVICE_PORT:-8040}"
    exec python -m uvicorn memory.app:app --host "${NERON_MEMORY_HOST:-0.0.0.0}" --port "${NERON_MEMORY_PORT:-8040}"
    ;;
  *)
    echo "Usage: $0 {core|llm|memory}"
    exit 1
    ;;
esac
