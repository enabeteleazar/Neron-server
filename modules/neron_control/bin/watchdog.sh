#!/bin/bash

# Charger Telegram depuis Homebox_AI/.env
if [ -f /opt/Homebox_AI/.env ]; then
    export $(grep -v '^#' /opt/Homebox_AI/.env | xargs)
fi

TG="/opt/homebox-control-plane/bin/telegram.sh"
LOG="/opt/homebox-control-plane/logs/watchdog.log"

echo "===== $(date) =====" >> $LOG

################################
# Docker check
################################

if ! systemctl is-active --quiet docker; then
    echo "Docker DOWN -> restart" >> $LOG
    systemctl restart docker
    $TG "Docker était DOWN -> restart effectué"
fi

################################
# RAM check
################################

RAM=$(free | awk '/Mem/ {printf("%.0f"), $3/$2 * 100.0}')
RAM_ALERT=90  # tu peux le changer ici ou le rendre configurable

if [ "$RAM" -gt "$RAM_ALERT" ]; then
    $TG "ALERTE : RAM critique ${RAM}%"
    echo "RAM critique ${RAM}%" >> $LOG
fi
