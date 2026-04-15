#!/usr/bin/env bash

set -e

SERVER_URL="http://localhost:8010"
LLM_URL="http://localhost:8765"

TIMEOUT=5
DEBUG=0
DEEP=0

for arg in "$@"; do
  [[ "$arg" == "--debug" ]] && DEBUG=1
  [[ "$arg" == "--deep" ]] && DEEP=1
done

# Colors
GREEN="\033[32m"
RED="\033[31m"
BLUE="\033[34m"
BOLD="\033[1m"
NC="\033[0m"

ok(){ echo -e "${GREEN}✔ $1${NC}"; }
fail(){ echo -e "${RED}✖ $1${NC}"; exit 1; }
step(){ echo -e "\n${BOLD}${BLUE}━━━ $1 ━━━${NC}"; }

# ━━━━━━━━━━━━━━━━━━━━━━━━
# CHECK PORT
# ━━━━━━━━━━━━━━━━━━━━━━━━
check_port(){
  if timeout $TIMEOUT bash -c "</dev/tcp/$1/$2" 2>/dev/null; then
    ok "Port $2 ouvert"
  else
    fail "Port $2 fermé"
  fi
}

# ━━━━━━━━━━━━━━━━━━━━━━━━
# CHECK HTTP
# ━━━━━━━━━━━━━━━━━━━━━━━━
check_http(){
  code=$(curl -s -o /dev/null -w "%{http_code}" "$1")
  [[ "$code" == "200" ]] && ok "$1 OK" || fail "$1 FAIL ($code)"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━
# VALID JSON
# ━━━━━━━━━━━━━━━━━━━━━━━━
validate_json(){
  echo "$1" | jq . >/dev/null 2>&1 || fail "JSON invalide"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━
# TEST LLM
# ━━━━━━━━━━━━━━━━━━━━━━━━
test_llm(){
  step "LLM DIRECT"

  response=$(curl -s --max-time $TIMEOUT \
    -X POST "$LLM_URL/generate" \
    -H "Content-Type: application/json" \
    -d '{"prompt":"ping"}')

  [[ "$DEBUG" == "1" ]] && echo "$response"

  [[ -z "$response" ]] && fail "LLM vide"
  validate_json "$response"

  ok "LLM OK"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━
# TEST E2E
# ━━━━━━━━━━━━━━━━━━━━━━━━
test_e2e(){
  step "E2E SERVER → LLM"

  response=$(curl -s --max-time $TIMEOUT \
    -X POST "$SERVER_URL/chat" \
    -H "Content-Type: application/json" \
    -d '{"message":"ping"}')

  [[ "$DEBUG" == "1" ]] && echo "$response"

  [[ -z "$response" ]] && fail "Server vide"
  validate_json "$response"

  ok "E2E OK"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━
# TEST LLM LENT
# ━━━━━━━━━━━━━━━━━━━━━━━━
test_slow(){
  step "SIMULATION LLM LENT"

  start=$(date +%s)

  curl -s --max-time 2 \
    -X POST "$LLM_URL/generate" \
    -H "Content-Type: application/json" \
    -d '{"prompt":"slow test"}' >/dev/null || true

  end=$(date +%s)
  duration=$((end-start))

  [[ $duration -ge 2 ]] && ok "Timeout OK" || fail "Timeout non respecté"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━
# TEST INVALID JSON
# ━━━━━━━━━━━━━━━━━━━━━━━━
test_invalid(){
  step "SIMULATION JSON INVALIDE"

  fake='invalid json'

  echo "$fake" | jq . >/dev/null 2>&1 && fail "JSON devrait échouer"

  ok "Détection JSON invalide OK"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━
clear
echo -e "${BOLD}NERON CI TEST${NC}"

step "PORTS"
check_port localhost 8010
check_port localhost 8765

step "HEALTH"
check_http "$SERVER_URL/health"
check_http "$LLM_URL/llm/health"

test_llm
test_e2e

if [[ "$DEEP" == "1" ]]; then
  test_slow
  test_invalid
fi

echo -e "\n${GREEN}${BOLD}ALL TESTS PASSED${NC}"
