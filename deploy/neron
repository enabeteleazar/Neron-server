#!/usr/bin/env bash
# /usr/local/bin/neron

set -euo pipefail

SERVER="neron.service"
LLM="neron-llm.service"
DOCTOR="neron-doctor.service"

SERVER_URL="http://localhost:8010"
LLM_URL="http://localhost:8765/llm"
DOCTOR_URL="http://localhost:8020"

LOG_TMP="/tmp/neron_logs.txt"

# ━━━━━━━━━━━━━━━━━━━━━━━
# UTILS
# ━━━━━━━━━━━━━━━━━━━━━━━
ok()   { echo "✔ $1"; }
warn() { echo "⚠ $1"; }
fail() { echo "✖ $1"; }

_require() {
  command -v "$1" >/dev/null 2>&1 || { warn "$1 non installé (apt install $1)"; return 1; }
}

# ━━━━━━━━━━━━━━━━━━━━━━━
# CORE
# ━━━━━━━━━━━━━━━━━━━━━━━
start()   { sudo systemctl start   "$SERVER" "$LLM" "$DOCTOR"; ok "started"; }
stop()    { sudo systemctl stop    "$SERVER" "$LLM" "$DOCTOR"; ok "stopped"; }
restart() { sudo systemctl restart "$SERVER" "$LLM" "$DOCTOR"; ok "restarted"; }

status() {
  sudo systemctl status "$SERVER" --no-pager
  sudo systemctl status "$LLM"    --no-pager
  sudo systemctl status "$DOCTOR" --no-pager

}

logs() {
  if _require ccze; then
    sudo journalctl -u "$SERVER" -u "$LLM" -u "$DOCTOR" -u ollama -f --no-pager | ccze -A
  else
    sudo journalctl -u "$SERVER" -u "$LLM" -u "$DOCTOR" -u ollama -f --no-pager
  fi
}

health() {
  curl -sf "$SERVER_URL/health" && echo "" || warn "server KO"
  curl -sf "$LLM_URL/health"    && echo "" || warn "llm KO"
  curl -sf "$DOCTOR_URL/health" && echo "" || warn "doctor KO"
}

# ━━━━━━━━━━━━━━━━━━━━━━━
# DOCTOR v3 (SCORE GLOBAL)
# ━━━━━━━━━━━━━━━━━━━━━━━
doctor() {
	make -C /etc/neron version
}

doctor_ports() {
  echo "🔎 Néron Doctor - Scan des ports critiques..."

  PORTS=(8010 8765 3000)

  for PORT in "${PORTS[@]}"; do
    echo ""
    echo "➡ Port $PORT"

    PID_INFO=$(ss -lptn "sport = :$PORT" 2>/dev/null)

    if [ -z "$PID_INFO" ]; then
      ok "Libre"
      continue
    fi

    warn "Occupé"
    echo "$PID_INFO"

    PID=$(echo "$PID_INFO" | grep -oP 'pid=\K[0-9]+' | head -n1)

    if [ -n "$PID" ]; then
      NAME=$(ps -p "$PID" -o comm= 2>/dev/null || echo "inconnu")
      echo "→ Process: $NAME (PID $PID)"

      if [[ "$NAME" == *"python"* || "$NAME" == *"uvicorn"* ]]; then
        warn "Process Néron probable détecté"
        if [ "${NERON_AUTO_FIX:-0}" == "1" ]; then
          echo "KILL AUTO PID $PID"
          kill -9 "$PID"
        else
          echo "Proposition: kill -9 $PID"
        fi
      fi
    fi
  done

  echo ""
  ok "Scan terminé"
}

# ━━━━━━━━━━━━━━━━━━━━━━━
# REPAIR v3 (INTELLIGENT FIX)
# ━━━━━━━━━━━━━━━━━━━━━━━
repair() {
  echo "━━ NERON REPAIR v3 ━━"

  # Vérification systemd d'abord — inutile de curl si le service ne tourne pas
  if ! systemctl is-active "$SERVER" >/dev/null 2>&1; then
    warn "server inactif — restart"
    sudo systemctl restart "$SERVER"
  fi
  if ! systemctl is-active "$LLM" >/dev/null 2>&1; then
    warn "llm inactif — restart"
    sudo systemctl restart "$LLM"
  fi
  if ! systemctl is-active "$DOCTOR" >/dev/null 2>&1; then
    warn "doctor inactif — restart"
    sudo systemctl restart "$DOCTOR"
  fi


  sleep 3

  # Vérification HTTP après délai de démarrage
  if curl -sf "$SERVER_URL/health" >/dev/null; then
    ok "server ok"
  else
    warn "server /health KO après restart"
  fi

  if curl -sf "$LLM_URL/health" >/dev/null; then
    ok "llm ok"
  else
    warn "llm /health KO après restart"
  fi
  if curl -sf "$DOCTOR_URL/health" >/dev/null; then
    ok "doctor ok"
  else
    warn "doctor /health KO après restart"
  fi

  ok "repair completed"
}

# ━━━━━━━━━━━━━━━━━━━━━━━
# PROFILE v3 (LATENCY + LOAD)
# ━━━━━━━━━━━━━━━━━━━━━━━
profile() {
  echo "━━ NERON PROFILE v3 ━━"

  echo ""
  echo "[LATENCY]"
  curl -o /dev/null -sf -w "server: %{time_total}s\n" "$SERVER_URL/health" || warn "server KO"
  curl -o /dev/null -sf -w "llm:    %{time_total}s\n" "$LLM_URL/health"    || warn "llm KO"
  curl -o /dev/null -sf -w "doctor: %{time_total}s\n" "$DOCTOR_URL/health" || warn "docor KO"


  echo ""
  echo "[SYSTEM LOAD]"
  uptime

  echo ""
  echo "[TOP CPU]"
  ps -eo pid,comm,%cpu --sort=-%cpu | head -n 6

  echo ""
  echo "[TOP RAM]"
  ps -eo pid,comm,%mem --sort=-%mem | head -n 6
}

# ━━━━━━━━━━━━━━━━━━━━━━━
# TRACE (LOG ANALYSIS)
# ━━━━━━━━━━━━━━━━━━━━━━━
trace() {
  echo "━━ NERON TRACE ━━"

  sudo journalctl -u "$SERVER" -u "$LLM" -n 200 --no-pager > "$LOG_TMP"

  echo ""
  echo "[ERROR PATTERNS]"
  grep -iE "error|fail|timeout|exception" "$LOG_TMP" | tail -n 20 || ok "aucune erreur"

  echo ""
  echo "[FREQUENCY ANALYSIS]"
  grep -iE "error|timeout|fail" "$LOG_TMP" | sort | uniq -c | sort -nr | head -n 10 || true
}

# ━━━━━━━━━━━━━━━━━━━━━━━
# BENCHMARK (LLM STRESS TEST)
# ━━━━━━━━━━━━━━━━━━━━━━━
benchmark() {
  echo "━━ NERON BENCHMARK ━━"

  for i in {1..5}; do
    curl -sf -o /dev/null -w "req $i: %{time_total}s\n" \
      -X POST "$LLM_URL/generate" \
      -H "Content-Type: application/json" \
      -d '{"prompt":"benchmark test"}' \
      || warn "req $i KO"
  done
}

# ━━━━━━━━━━━━━━━━━━━━━━━
# REPORT (JSON EXPORT)
# ━━━━━━━━━━━━━━━━━━━━━━━
report() {
  echo "━━ NERON REPORT ━━"

  _require jq || return 1

  server_health=$(curl -sf "$SERVER_URL/health" 2>/dev/null || echo "KO")
  llm_health=$(curl -sf "$LLM_URL/health"       2>/dev/null || echo "KO")

  jq -n \
    --arg server  "$server_health" \
    --arg llm     "$llm_health" \
    --arg uptime  "$(uptime)" \
    --arg ts      "$(date -Iseconds)" \
    '{server: $server, llm: $llm, uptime: $uptime, timestamp: $ts}'
}

# ━━━━━━━━━━━━━━━━━━━━━━━
# ROUTER
# ━━━━━━━━━━━━━━━━━━━━━━━
case "${1:-}" in
  start)        start ;;
  stop)         stop ;;
  restart)      restart ;;
  status)       status ;;
  logs)         logs ;;
  health)       health ;;
  doctor)       doctor ;;
  doctor-ports) doctor_ports ;;
  repair)       repair ;;
  profile)      profile ;;
  trace)        trace ;;
  benchmark)    benchmark ;;
  report)       report ;;
  *)
    echo "Usage: neronctl {start|stop|restart|status|logs|health|doctor|doctor-ports|repair|profile|trace|benchmark|report}"
    ;;
esac
