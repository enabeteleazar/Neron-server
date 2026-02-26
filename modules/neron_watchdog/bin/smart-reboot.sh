#!/bin/bash

TG="/opt/homebox-control-plane/bin/telegram.sh"
LOG="/opt/homebox-control-plane/logs/reboot.log"

$TG "Reboot intelligent lancé"

################################
# LOCK FILE
################################

LOCK_FILE="/opt/homebox-control-plane/run/reboot.lock"
if [ -f "$LOCK_FILE" ]; then
    $TG "Reboot annulé : LOCK actif"
    exit 1
fi

################################
# Stop Docker propre
################################

for dir in /opt/*; do
    if [ -f "$dir/docker-compose.yaml" ]; then
        (cd $dir && docker compose down)
        $TG "Stack $dir arrêtée"
    fi
done

sync
sleep 5

$TG "Serveur en reboot maintenant"
reboot
