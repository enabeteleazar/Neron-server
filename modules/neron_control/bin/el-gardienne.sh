#!/bin/bash
# El Gardienne - Surveillance complète Homebox

TG="/opt/homebox-control-plane/bin/telegram.sh"
LOG="/opt/homebox-control-plane/logs/el-gardienne.log"

# Charger .env Telegram
if [ -f /opt/Homebox_AI/.env ]; then
    export $(grep -v '^#' /opt/Homebox_AI/.env | xargs)
fi

echo "===== $(date) =====" >> $LOG

FAIL=0

# ---------- Fonctions ----------
check_port() {
    local PORT=$1
    local NAME=$2
    if ! ss -tuln | grep -q ":$PORT "; then
        echo "CRITICAL: $NAME (port $PORT) fermé" >> $LOG
        $TG "ALERTE : $NAME (port $PORT) fermé"
        FAIL=1
    else
        echo "OK: $NAME (port $PORT)" >> $LOG
    fi
}

check_service() {
    local SERVICE=$1
    if ! systemctl is-active --quiet $SERVICE; then
        echo "CRITICAL: Service $SERVICE DOWN" >> $LOG
        $TG "ALERTE : Service $SERVICE DOWN"
        FAIL=1
    else
        echo "OK: Service $SERVICE actif" >> $LOG
    fi
}

check_docker_container() {
    local CONTAINER=$1
    if ! docker ps --format '{{.Names}}' | grep -q "^$CONTAINER\$"; then
        echo "CRITICAL: Container Docker $CONTAINER non lancé" >> $LOG
        $TG "ALERTE : Container Docker $CONTAINER non lancé"
        FAIL=1
    else
        echo "OK: Container Docker $CONTAINER actif" >> $LOG
    fi
}

check_disk() {
    local THRESHOLD=$1
    df -h --output=pcent,target | tail -n +2 | while read USAGE MOUNT; do
        USAGE_NUM=$(echo $USAGE | tr -dc '0-9')
        if [ "$USAGE_NUM" -ge "$THRESHOLD" ]; then
            echo "CRITICAL: Disque $MOUNT ${USAGE_NUM}% utilisé" >> $LOG
            $TG "ALERTE : Disque $MOUNT ${USAGE_NUM}% utilisé"
            FAIL=1
        fi
    done
}

check_cpu_ram() {
    CPU=$(top -bn1 | grep "Cpu(s)" | awk '{print $2+$4}')
    RAM=$(free | awk '/Mem/ {printf("%.0f"), $3/$2 * 100.0}')
    if [ "$CPU" -gt 90 ]; then
        echo "ALERTE: CPU critique ${CPU}%" >> $LOG
        $TG "ALERTE : CPU critique ${CPU}%"
    fi
    if [ "$RAM" -gt 90 ]; then
        echo "ALERTE: RAM critique ${RAM}%" >> $LOG
        $TG "ALERTE : RAM critique ${RAM}%"
    fi
}

# ---------- Ports à surveiller ----------
declare -A PORTS
PORTS=( 
    [Home_Assistant]=8123
    [Prometheus]=9090
    [MQTT]=1883
    [CUPS]=631
    [SSH]=22
)

for NAME in "${!PORTS[@]}"; do
    check_port ${PORTS[$NAME]} $NAME
done

# ---------- Services systemd ----------
SERVICES=(docker systemd-logind getty@tty1 packagekit unattended-upgrades cups-browsed)
for S in "${SERVICES[@]}"; do
    check_service $S
done

# ---------- Containers Docker spécifiques ----------
CONTAINERS=(neron-core neron-llm home-assistant prometheus)
for C in "${CONTAINERS[@]}"; do
    check_docker_container $C
done

# ---------- CPU, RAM et Disque ----------
check_cpu_ram
check_disk 90

echo "===== Fin de check =====" >> $LOG
