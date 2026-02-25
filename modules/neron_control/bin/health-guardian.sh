#!/bin/bash

TG="/opt/homebox-control-plane/bin/telegram.sh"

FAIL=0

check_port () {
    if ! ss -tuln | grep -q ":$1 "; then
        $TG "CRITICAL : Port $1 fermé"
        FAIL=1
    fi
}

# Ports critiques (Home Assistant et Prometheus)
PORT_HOME_ASSISTANT=8123
PORT_PROMETHEUS=9090

check_port $PORT_HOME_ASSISTANT
check_port $PORT_PROMETHEUS

# Docker
if ! systemctl is-active --quiet docker; then
    $TG "CRITICAL : Docker DOWN"
    FAIL=1
fi

if [ $FAIL -eq 0 ]; then
    echo "Healthy"
fi
