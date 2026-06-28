#!/usr/bin/env bash
# =============================================================================
# neron-boot.sh — Démarrage ordonné et sécurisé de Néron via systemd
# =============================================================================
# Usage : bash neron-boot.sh [--restart] [--logs]
#
# Corrections v2.2.2 :
#   • Purge des instances orphelines avant démarrage (fix 409 Telegram)
#   • URL health check corrigée : /llm/health (était /health)
#   • Attente active du port 8765 via curl sur la bonne route
#   • Vérification de conflit Telegram avant démarrage (pas après)
#   • Délai post-arrêt augmenté pour laisser Telegram libérer le polling
# =============================================================================

clear
set -euo pipefail

# ─── Couleurs ─────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

# ─── Config ───────────────────────────────────────────────────────────────────
LLM_SERVICE="neron-llm.service"
MAIN_SERVICE="neron-server.service"
LLM_HEALTH_URL="http://localhost:8765/llm/health"   # FIX: était /health
LLM_WAIT_MAX=45                                      # augmenté pour cold-start Ollama
LLM_WAIT_INTERVAL=2
TELEGRAM_DRAIN_WAIT=5                                # secondes après arrêt pour libérer polling

# ─── Helpers ──────────────────────────────────────────────────────────────────
log()  { echo -e "${CYAN}[$(date +%H:%M:%S)]${RESET} $*"; }
ok()   { echo -e "${GREEN}[$(date +%H:%M:%S)] ✓${RESET} $*"; }
warn() { echo -e "${YELLOW}[$(date +%H:%M:%S)] ⚠${RESET}  $*"; }
fail() { echo -e "${RED}[$(date +%H:%M:%S)] ✗${RESET} $*" >&2; }

slow_echo() {
  local msg="$1"
  for (( i=0; i<${#msg}; i++ )); do
    printf '%s' "${msg:$i:1}"
    sleep 0.015
  done
  echo
}

spinner() {
  local pid=$1 msg="${2:-Patientez…}"
  local frames=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')
  local i=0
  while kill -0 "$pid" 2>/dev/null; do
    printf "\r${DIM}  %s %s${RESET}" "${frames[i % ${#frames[@]}]}" "$msg"
    sleep 0.1
    (( i++ ))
  done
  printf "\r%-60s\r" " "
}

banner() {
  echo
  echo -e "${BOLD}${CYAN}╔══════════════════════════════════════╗${RESET}"
  echo -e "${BOLD}${CYAN}║        NÉRON — BOOT SEQUENCE         ║${RESET}"
  echo -e "${BOLD}${CYAN}╚══════════════════════════════════════╝${RESET}"
  echo
}

# ─── Arguments ────────────────────────────────────────────────────────────────
DO_RESTART=false
SHOW_LOGS=false
for arg in "$@"; do
  case $arg in
    --restart) DO_RESTART=true ;;
    --logs)    SHOW_LOGS=true ;;
  esac
done

# ─── Vérifications prérequis ──────────────────────────────────────────────────
check_prereqs() {
  log "Vérification des prérequis…"

  local missing=0

  if ! command -v curl &>/dev/null; then
    fail "curl non trouvé — requis pour les health checks"
    (( missing++ ))
  fi

  for svc in "$LLM_SERVICE" "$MAIN_SERVICE"; do
    if ! systemctl list-unit-files "$svc" 2>/dev/null | grep -q "$svc"; then
      fail "Service systemd introuvable : $svc"
      (( missing++ ))
    fi
  done

  if (( missing > 0 )); then
    fail "Abandon : $missing prérequis manquant(s)."
    exit 1
  fi

  ok "Prérequis OK"
}

# ─── Purge des instances orphelines ──────────────────────────────────────────
# Tue tout processus uvicorn/python qui traînerait hors du contrôle systemd.
# C'est la cause principale des 409 Conflict Telegram : une ancienne instance
# continue à faire getUpdates en parallèle du nouveau bot.
kill_orphans() {
  log "Vérification des instances orphelines…"

  local found=0

  # uvicorn core.app (serveur principal)
  local pids
  pids=$(pgrep -f "uvicorn core.app" 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    warn "Instance uvicorn core.app orpheline détectée (PIDs: $pids) — kill"
    kill $pids 2>/dev/null || true
    (( found++ ))
  fi

  # uvicorn neron_llm (service LLM)
  pids=$(pgrep -f "uvicorn neron_llm\|uvicorn.*8765" 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    warn "Instance uvicorn LLM orpheline détectée (PIDs: $pids) — kill"
    kill $pids 2>/dev/null || true
    (( found++ ))
  fi

  if (( found > 0 )); then
    sleep 2   # laisser les sockets se libérer
    ok "Instances orphelines purgées ($found groupe(s))"
  else
    ok "Aucune instance orpheline détectée"
  fi
}

# ─── Arrêt propre des services ────────────────────────────────────────────────
stop_services() {
  log "Arrêt des services en cours…"

  # Arrêt dans l'ordre inverse du démarrage
  for svc in "$MAIN_SERVICE" "$LLM_SERVICE"; do
    if systemctl is-active --quiet "$svc"; then
      warn "Arrêt de $svc…"
      sudo systemctl stop "$svc"
      ok "$svc arrêté"
    else
      log "$svc déjà inactif"
    fi
  done

  # FIX : délai explicite pour que Telegram libère le long-polling
  # Sans cette attente, le nouveau bot démarre avant que l'ancien ait
  # reçu la réponse de son dernier getUpdates → 409 Conflict immédiat.
  log "Attente drainage Telegram (${TELEGRAM_DRAIN_WAIT}s)…"
  sleep "$TELEGRAM_DRAIN_WAIT"

  # Purge après arrêt systemd au cas où des workers survivent
  kill_orphans
}

# ─── Étape 1 : LLM service ───────────────────────────────────────────────────
start_llm() {
  log "Étape 1/2 — Démarrage de $LLM_SERVICE…"

  sudo systemctl start "$LLM_SERVICE"

  if ! systemctl is-active --quiet "$LLM_SERVICE"; then
    fail "$LLM_SERVICE a échoué au démarrage"
    echo
    journalctl -u "$LLM_SERVICE" -n 20 --no-pager | sed 's/^/  /'
    exit 1
  fi

  # Attente active sur /llm/health (la vraie route, pas /health)
  local elapsed=0
  local ready=false

  while (( elapsed < LLM_WAIT_MAX )); do
    if curl -sf "$LLM_HEALTH_URL" > /dev/null 2>&1; then
      ready=true
      break
    fi

    # Détection d'un crash prématuré
    if ! systemctl is-active --quiet "$LLM_SERVICE"; then
      fail "$LLM_SERVICE s'est arrêté de façon inattendue"
      echo
      journalctl -u "$LLM_SERVICE" -n 20 --no-pager | sed 's/^/  /'
      exit 1
    fi

    printf "\r${DIM}  ⏳ Attente LLM health (/llm/health)… %ds / %ds${RESET}" \
      "$elapsed" "$LLM_WAIT_MAX"
    sleep "$LLM_WAIT_INTERVAL"
    (( elapsed += LLM_WAIT_INTERVAL ))
  done

  printf "\r%-60s\r" " "

  if ! $ready; then
    warn "Endpoint /llm/health non répondu après ${LLM_WAIT_MAX}s"
    warn "Service actif mais LLM peut ne pas être totalement prêt"
    warn "Poursuite avec 3s supplémentaires…"
    sleep 3
  else
    # Afficher l'état du provider Ollama depuis le health check
    local health_json
    health_json=$(curl -sf "$LLM_HEALTH_URL" 2>/dev/null || echo '{}')
    local ollama_status
    ollama_status=$(echo "$health_json" | grep -o '"ollama":"[^"]*"' | cut -d'"' -f4 || echo "?")
    ok "LLM service prêt sur :8765 — Ollama: ${ollama_status}"
  fi
}

# ─── Étape 2 : Serveur principal ─────────────────────────────────────────────
start_server() {
  log "Étape 2/2 — Démarrage de $MAIN_SERVICE…"

  sudo systemctl start "$MAIN_SERVICE"

  local elapsed=0
  local ready=false

  while (( elapsed < 30 )); do
    if ! systemctl is-active --quiet "$MAIN_SERVICE"; then
      fail "$MAIN_SERVICE s'est arrêté de façon inattendue"
      echo
      journalctl -u "$MAIN_SERVICE" -n 20 --no-pager | sed 's/^/  /'
      exit 1
    fi
    if journalctl -u "$MAIN_SERVICE" -n 50 --no-pager 2>/dev/null \
        | grep -q "Application startup complete"; then
      ready=true
      break
    fi
    printf "\r${DIM}  ⏳ Attente serveur principal… %ds / 30s${RESET}" "$elapsed"
    sleep 1
    (( elapsed++ ))
  done

  printf "\r%-60s\r" " "

  if ! $ready; then
    warn "Timeout 30s — $MAIN_SERVICE actif mais startup non confirmé dans les logs"
  else
    ok "Serveur principal prêt sur :8010"
  fi
}

# ─── Vérifications post-démarrage ────────────────────────────────────────────
post_check() {
  log "Vérifications post-démarrage…"

  local warnings=0

  # RAM
  local ram_pct
  ram_pct=$(free | awk '/^Mem:/ { printf "%.0f", $3/$2 * 100 }')
  if (( ram_pct > 90 )); then
    warn "RAM élevée : ${ram_pct}%"
    (( warnings++ ))
  else
    ok "RAM : ${ram_pct}%"
  fi

  # Conflits Telegram résiduels — vérifier après quelques secondes de polling
  log "Stabilisation Telegram (5s)…"
  sleep 5

  local conflict_count
  conflict_count=$(journalctl -u "$MAIN_SERVICE" --since "30 seconds ago" \
    --no-pager 2>/dev/null | grep -c "409 Conflict" || true)
  if (( conflict_count > 0 )); then
    warn "Conflits Telegram 409 résiduels ($conflict_count dans les 30 dernières secondes)"
    warn "Une ancienne instance est peut-être encore active — relancer avec --restart"
    (( warnings++ ))
  else
    ok "Telegram : aucun conflit 409 détecté"
  fi

  # Services toujours UP
  if systemctl is-active --quiet "$LLM_SERVICE"; then
    ok "$LLM_SERVICE : actif"
  else
    fail "$LLM_SERVICE : inactif !"
    (( warnings++ ))
  fi

  if systemctl is-active --quiet "$MAIN_SERVICE"; then
    ok "$MAIN_SERVICE : actif"
  else
    fail "$MAIN_SERVICE : inactif !"
    (( warnings++ ))
  fi

  # LLM health final
  if curl -sf "$LLM_HEALTH_URL" > /dev/null 2>&1; then
    ok "LLM health check : OK"
  else
    warn "LLM health check non répondu — vérifier journalctl -u $LLM_SERVICE"
    (( warnings++ ))
  fi

  echo
  if (( warnings == 0 )); then
    echo -e "${GREEN}${BOLD}  ✓ Néron opérationnel — 0 avertissement${RESET}"
  else
    echo -e "${YELLOW}${BOLD}  ⚠ Néron démarré avec $warnings avertissement(s)${RESET}"
  fi
  echo
  echo -e "${DIM}  Logs LLM    : journalctl -u $LLM_SERVICE -f${RESET}"
  echo -e "${DIM}  Logs Server : journalctl -u $MAIN_SERVICE -f${RESET}"
  echo
}

# ─── Logs live ────────────────────────────────────────────────────────────────
follow_logs() {
  log "Logs en direct (Ctrl+C pour quitter) :"
  echo -e "${DIM}─────────────────────────────────────────${RESET}"
  journalctl -u "$LLM_SERVICE" -u "$MAIN_SERVICE" -f --no-pager
}

# ─── Main ─────────────────────────────────────────────────────────────────────
banner
slow_echo "  Initialisation séquence de démarrage Néron v2.2.2…"
echo

check_prereqs

if $DO_RESTART || \
   systemctl is-active --quiet "$LLM_SERVICE" || \
   systemctl is-active --quiet "$MAIN_SERVICE"; then
  stop_services
else
  # Même si aucun service n'est actif, purger les éventuels orphelins
  kill_orphans
fi

start_llm
start_server
post_check

if $SHOW_LOGS; then
  follow_logs
fi
