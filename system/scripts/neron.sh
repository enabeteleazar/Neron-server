#!/usr/bin/env bash

clear
set -euo pipefail

REPO="/etc/neronOS"
VENV="$REPO/venv"
API_URL="${NERON_API_URL:-http://localhost:8010}"

# Inventaire decouvert, jamais fige : tout ce qui porte le prefixe neron-
# ou une instance du gabarit neron@. ollama reste explicite, il n a pas le prefixe.
mapfile -t SERVICES < <(
  systemctl list-units 'neron*' --type=service --all --no-legend \
    | sed 's/^[^a-zA-Z]*//' \
    | awk '{print $1}'
)
SERVICES+=("ollama.service")

ok() {
  echo "✔ $1"
}

warn() {
  echo "⚠ $1"
}


# ─────────────────────────────────────────────────────────────
# AIDE
# ─────────────────────────────────────────────────────────────

show_help() {
  cat <<'EOF'
Néron CLI

Usage:
  neron <commande>

Commandes utilisateur:
  status              Affiche l'état rapide de Néron
  version             Affiche les versions du Core et des submodules
  goal "demande"      Envoie un objectif à Néron
  chat "message"      Envoie un message simple à Néron
  registry            Affiche la topologie complète des services
  services            Affiche la liste compacte des services
  service <nom>       Affiche le détail d'un service

Développement:
  Utiliser make

Exemples:
  neron status
  neron version
  neron goal "Créer un agent de test"
  neron chat "Bonjour Néron"
EOF
}

usage() {
  cat <<EOF

Néron CLI

Usage:
  neron <commande>

Services:
  start
  stop
  restart
  status
  journal

Maintenance:
  clean
  backup
  restore

Outils:
  config
  telegram
  ollama

Tâches:
  task
  tasks
  task-show
  task-logs

Utilisateur:
  version
  goal "demande"
  chat "message"
  help

EOF
}


# ─────────────────────────────────────────────────────────────
# COMMANDES UTILISATEUR
# ─────────────────────────────────────────────────────────────

cmd_status() {
  for service in "${SERVICES[@]}"; do
    status=$(systemctl is-active "$service")

    case "$status" in
        active)   icon="✅" ;;
        inactive) icon="⚪" ;;
        failed)   icon="❌" ;;
        *)        icon="⚠️" ;;
    esac

    printf "%-35s %s %s\n" "$service" "$icon" "$status"
done
}

cmd_version() {
  cd "$REPO"

  echo "NÉRON VERSION"
  echo "============="
  echo

  echo "NeronOS:"
  echo " Branch : $(git branch --show-current)"
  echo " Commit : $(git rev-parse --short HEAD)"
  echo " Version: $(git describe --tags --always)"
  echo

  echo "Submodules:"

  git submodule foreach --quiet '
    branch=$(git branch --show-current)
    [ -z "$branch" ] && branch="detached"

    echo " $name:"
    echo "   Branch : $branch"
    echo "   Commit : $(git rev-parse --short HEAD)"
    echo "   Version: $(git describe --tags --always)"
    echo
  ' || true
}

cmd_goal() {
  local goal="${*:-}"

  if [ -z "$goal" ]; then
    echo "Erreur: objectif manquant."
    echo 'Exemple: neron goal "Créer un agent de test"'
    exit 1
  fi

  curl -s \
    -X POST "$API_URL/goal" \
    -H "Content-Type: application/json" \
    -d "{\"goal\":\"$goal\"}"

  echo
}

cmd_chat() {
  local message="${*:-}"

  if [ -z "$message" ]; then
    echo "Erreur: message manquant."
    echo 'Exemple: neron chat "Bonjour Néron"'
    exit 1
  fi

  curl -s \
    -X POST "$API_URL/chat" \
    -H "Content-Type: application/json" \
    -d "{\"message\":\"$message\"}"

  echo
}

cmd_registry_cli() {
  PYTHONPATH="$REPO${PYTHONPATH:+:$PYTHONPATH}" \
    "$VENV/bin/python" -m server.common.cli "$@"
}


# ─────────────────────────────────────────────────────────────
# SERVICES
# ─────────────────────────────────────────────────────────────

start() {
  sudo systemctl start neron.target
  ok "coeur démarré (neron.target)"
}

stop() {
  sudo systemctl stop neron.target
  ok "coeur arrêté (neron.target)"
}

restart() {
  sudo systemctl restart neron.target
  ok "coeur redémarré (neron.target)"
  status
}

status() {
  for service in "${SERVICES[@]}"; do
    state="$(systemctl is-active "$service" 2>/dev/null || true)"

    case "$state" in
      active) icon="✅" ;;
      inactive) icon="⚪" ;;
      activating) icon="🟡" ;;
      failed) icon="❌" ;;
      *) icon="⚠️"; state="${state:-unknown}" ;;
    esac

    printf "%-35s %s %s\n" "$service" "$icon" "$state"
  done
}

journal() {
  journalctl $(systemctl list-units --type=service --all --no-legend | awk '/neron-/ {print "-u", $1}') -f | ccze -A
}


# ─────────────────────────────────────────────────────────────
# MAINTENANCE
# ─────────────────────────────────────────────────────────────

clean() {
    find "$REPO" -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete

    for cache in __pycache__ .pytest_cache .mypy_cache .ruff_cache; do
        find "$REPO" -type d -name "$cache" -prune -exec rm -rf {} +
    done

    ok "caches nettoyés"
}

backup() {
  bash "$REPO/scripts/backup.sh" backup
}

restore() {
  bash "$REPO/scripts/backup.sh" restore
}


# ─────────────────────────────────────────────────────────────
# OUTILS
# ─────────────────────────────────────────────────────────────

config() {
  bash "$REPO/scripts/neron.sh"
}

telegram() {
  bash "$REPO/scripts/telegram.sh"
}

ollama() {
  bash "$REPO/scripts/ollama.sh"
}


# ─────────────────────────────────────────────────────────────
# TASKS
# ─────────────────────────────────────────────────────────────

task() {
  need_neronctl
  neronctl task "$@"
}

tasks() {
  need_neronctl
  neronctl task list "$@"
}

task_show() {
  need_neronctl
  neronctl task show "$@"
}

task_logs() {
  need_neronctl
  neronctl task logs "$@"
}


# ─────────────────────────────────────────────────────────────
# ROUTING
# ─────────────────────────────────────────────────────────────

case "${1:-help}" in

  help|-h|--help)
    show_help
    ;;

  start)
    start
    ;;

  stop)
    stop
    ;;

  restart)
    restart
    ;;

  status)
    status
    ;;

  journal)
    journal
    ;;

  clean)
    clean
    ;;

  backup)
    backup
    ;;

  restore)
    restore
    ;;

  config)
    config
    ;;

  telegram)
    telegram
    ;;

  ollama)
    ollama
    ;;

  client-install)
    client_install
    ;;

  client-start)
    client_start
    ;;

  task)
    shift
    task "$@"
    ;;

  tasks)
    shift
    tasks "$@"
    ;;

  task-show)
    shift
    task_show "$@"
    ;;

  task-logs)
    shift
    task_logs "$@"
    ;;

  version)
    cmd_version
    ;;

  goal)
    shift
    cmd_goal "$@"
    ;;

  chat)
    shift
    cmd_chat "$@"
    ;;

  registry|services)
    cmd_registry_cli "$1"
    ;;

  service)
    shift
    cmd_registry_cli service "$@"
    ;;

  *)
    echo "Commande inconnue: ${1}"
    echo
    usage
    exit 1
    ;;

esac
