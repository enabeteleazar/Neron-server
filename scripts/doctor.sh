#!/usr/bin/env bash

set -e

# =========================
# CONFIG
# =========================
SERVER_URL="http://localhost:8010"
LLM_URL="http://localhost:8765"
API_URL="$SERVER_URL/health"

TIMEOUT=5
DEBUG=0
DEEP=0
MODE="all"

# =========================
# ARGS
# =========================
for arg in "$@"; do
  case "$arg" in
    --debug) DEBUG=1 ;;
    --deep) DEEP=1 ;;
    --test) MODE="test" ;;
    --info) MODE="info" ;;
  esac
done

# =========================
# COLORS
# =========================
BOLD="\033[1m"
BLUE="\033[34m"
GREEN="\033[32m"
RED="\033[31m"
YELLOW="\033[33m"
NC="\033[0m"

# =========================
# UI
# =========================
ok(){ echo -e "${GREEN}✔ $1${NC}"; }
fail(){ echo -e "${RED}✖ $1${NC}"; exit 1; }
warn(){ echo -e "${YELLOW}⚠ $1${NC}"; }
step(){ echo -e "\n${BOLD}${BLUE}━━━ $1 ━━━${NC}"; }

# =========================
# CORE UTILS
# =========================
check_port(){
  if timeout $TIMEOUT bash -c "</dev/tcp/$1/$2" 2>/dev/null; then
    ok "Port $2 ouvert"
  else
    fail "Port $2 fermé"
  fi
}

check_http(){
  code=$(curl -s -o /dev/null -w "%{http_code}" "$1")
  [[ "$code" == "200" ]] && ok "$1 OK" || fail "$1 FAIL ($code)"
}

validate_json(){
  echo "$1" | jq . >/dev/null 2>&1 || fail "JSON invalide"
}

# =========================
# TESTS
# =========================
test_ports(){
  step "PORTS"
  check_port localhost 8010
  check_port localhost 8765
}

test_health(){
  step "HEALTH"
  check_http "$SERVER_URL/health"
  check_http "$LLM_URL/llm/health"
}

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

test_deep(){
  step "TESTS AVANCÉS"

  # Timeout test
  start=$(date +%s)
  curl -s --max-time 2 -X POST "$LLM_URL/generate" \
    -H "Content-Type: application/json" \
    -d '{"prompt":"slow"}' >/dev/null || true
  end=$(date +%s)

  [[ $((end-start)) -ge 2 ]] && ok "Timeout OK" || fail "Timeout FAIL"

  # JSON invalide
  echo "invalid json" | jq . >/dev/null 2>&1 && fail "JSON devrait échouer"
  ok "Détection JSON invalide OK"
}

# =========================
# INFO SYSTEM
# =========================
info_python(){
  step "PYTHON"

  if command -v python3 >/dev/null; then
    ok "$(python3 --version)"
    echo "Path: $(command -v python3)"
  else
    fail "Python3 absent"
  fi
}

info_api(){
  step "API"

  HTTP_CODE=$(curl -s -o /tmp/neron_api.json -w "%{http_code}" "$API_URL" || true)
  API_RESPONSE=$(cat /tmp/neron_api.json 2>/dev/null || true)

  if [ "$HTTP_CODE" != "200" ]; then
    fail "API HTTP $HTTP_CODE"
  fi

  echo "$API_RESPONSE" | python3 - << 'EOF'
import sys, json
try:
    d = json.load(sys.stdin)
    print(f"✔ Status  : {d.get('status')}")
    print(f"✔ Version : {d.get('version')}")
except:
    print("❌ API invalide")
EOF
}

info_ollama(){
  step "OLLAMA"

  if command -v ollama >/dev/null; then
    ok "Ollama installé"
    ollama list | awk 'NR>1 {print "✔ " $1}'
  else
    warn "Ollama absent"
  fi

  systemctl is-active --quiet ollama && ok "Service actif" || warn "Service inactif"
}

info_services(){
  step "SERVICES"

  SERVICES=(
    "neron.service"
    "neron-llm.service"
    "neron-homeassistant.service"
    "neron-client.service"
  )

  for s in "${SERVICES[@]}"; do
    printf "  %-30s" "$s"

    if [ ! -f "/etc/systemd/system/$s" ]; then
      echo -e "${YELLOW}non installé${NC}"
      continue
    fi

    systemctl is-active --quiet "$s" \
      && echo -e "${GREEN}actif${NC}" \
      || echo -e "${RED}inactif${NC}"
  done
}

info_system(){
  step "SYSTEM"

  CPU=$(grep -m1 "model name" /proc/cpuinfo | cut -d: -f2)
  RAM=$(free -h | awk '/Mem:/ {print $3 "/" $2}')
  DISK=$(df -h / | awk 'NR==2 {print $3 "/" $2 " (" $5 ")"}')

  echo "CPU  : $CPU"
  echo "RAM  : $RAM"
  echo "DISK : $DISK"
}

# =========================
# RUN MODES
# =========================
run_tests(){
  test_ports
  test_health
  test_llm
  test_e2e
  [[ "$DEEP" == "1" ]] && test_deep
}

run_info(){
  info_python
  info_api
  info_ollama
  info_services
  info_system
}

# =========================
# MAIN
# =========================
clear
echo -e "${BOLD}${BLUE}NÉRON DOCTOR${NC}"

case "$MODE" in
  test) run_tests ;;
  info) run_info ;;
  all)
    run_info
    run_tests
    ;;
esac

echo -e "\n${GREEN}${BOLD}✔ DONE${NC}"
