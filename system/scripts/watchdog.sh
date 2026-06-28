#!/usr/bin/env bash

LOG="/var/log/neron-watchdog.log"
BASE_DIR="/etc/neron"

function log(){
  echo "$(date) - $1" >> $LOG
}

function restart_llm(){
  log "Restart LLM"
  systemctl restart neron-llm
}

function restart_server(){
  log "Restart SERVER"
  systemctl restart neron-server
}

# CHECK LLM
curl -s http://localhost:8765/health >/dev/null
if [[ $? -ne 0 ]]; then
  log "LLM DOWN"
  restart_llm
fi

# CHECK SERVER
curl -s http://localhost:8010/health >/dev/null
if [[ $? -ne 0 ]]; then
  log "SERVER DOWN"
  restart_server
fi

# TEST GLOBAL
bash "$BASE_DIR/scripts/test.sh" >/dev/null 2>&1
if [[ $? -ne 0 ]]; then
  log "GLOBAL TEST FAILED → RESTART ALL"
  systemctl restart neron-server
  systemctl restart neron-llm
fi
