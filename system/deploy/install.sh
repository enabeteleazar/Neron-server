#!/usr/bin/env bash
# Installe (ou verifie) la configuration de deploiement NeronOS.
#   ./install.sh check     compare sans rien modifier
#   sudo ./install.sh install   copie vers le systeme
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:-check}"
RC=0

# source:cible
MAP=(
  "$HERE/env/common.env:/etc/neronOS/env/common.env"
  "$HERE/caddy/Caddyfile:/etc/caddy/Caddyfile"
)
for u in "$HERE"/systemd/*; do
  MAP+=("$u:/etc/systemd/system/$(basename "$u")")
done

case "$MODE" in
  check)
    for pair in "${MAP[@]}"; do
      src="${pair%%:*}"; dst="${pair#*:}"
      if [ ! -e "$dst" ]; then
        echo "MANQUANT   $dst"; RC=1
      elif ! diff -rq "$src" "$dst" >/dev/null 2>&1; then
        echo "DIVERGENT  $dst"; RC=1
      else
        echo "OK         $dst"
      fi
    done
    exit $RC
    ;;
  install)
    [ "$(id -u)" -eq 0 ] || { echo "install requiert root" >&2; exit 1; }
    for pair in "${MAP[@]}"; do
      src="${pair%%:*}"; dst="${pair#*:}"
      mkdir -p "$(dirname "$dst")"
      cp -r "$src" "$(dirname "$dst")/"
      echo "installe   $dst"
    done
    systemctl daemon-reload
    caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
    systemctl reload caddy
    echo "Termine. Aucun service n a ete demarre ni active volontairement."
    ;;
  *)
    echo "usage: $0 [check|install]" >&2; exit 2
    ;;
esac
