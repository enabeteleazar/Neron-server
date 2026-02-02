#!/bin/bash
echo -e "\033[1;34m[NERON] Vérification des services...\033[0m"
printf "%-20s %-8s %-10s %-12s %-15s\n" "Container" "UP" "Healthy" "Endpoint" "Test Unit"

for container in $(docker ps -a --format "{{.Names}}" | grep neron); do
    # UP
    status=$(docker inspect --format '{{.State.Status}}' $container)
    up="❌"
    [[ "$status" == "running" ]] && up="✅"

    # HEALTH
    health=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' $container)
    [[ "$health" == "healthy" ]] && health="✅" || [[ "$health" == "none" ]] && health="N/A" || health="❌"

    # Endpoint (exemple HTTP sur /health)
    port=$(docker inspect --format '{{(index (index .NetworkSettings.Ports "8000/tcp") 0).HostPort}}' $container 2>/dev/null)
    if [[ -n "$port" ]]; then
        code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/health 2>/dev/null)
        [[ "$code" == "200" ]] && endpoint="✅" || endpoint="❌"
    else
        endpoint="N/A"
    fi

    # Test unitaire simple
    if [[ "$container" == *core* ]]; then
        docker exec $container python3 /app/test_core_llm.py &>/dev/null && testu="✅" || testu="❌"
    else
        testu="N/A"
    fi

    printf "%-20s %-8s %-10s %-12s %-15s\n" $container $up $health $endpoint $testu
done
