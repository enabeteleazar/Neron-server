#!/bin/bash

echo -e "\033[1;34m[HOMEBOX] Vérification de l'état des services...\033[0m"

# 🔥 Récupère automatiquement tous les noms des containers existants
mapfile -t services < <(docker ps -a --format "{{.Names}}")

offline_list=()   # stockera les containers OFFLINE
online_count=0
offline_count=0

echo -e "\n📊 Liste des services détectés : ${#services[@]}"
echo "--------------------------------------------"

# Boucle de vérification
for s in "${services[@]}"; do
    status=$(docker ps --filter "name=^${s}$" --format "{{.Status}}")

    if [[ -z "$status" ]]; then
        echo -e "🔴 \033[1;31m$s : OFFLINE\033[0m"
        offline_list+=("$s")
        ((offline_count++))
    else
        echo -e "🟢 \033[1;32m$s : $status\033[0m"
        ((online_count++))
    fi
done

# === RÉSUMÉ =====================================
echo -e "\n==============================="
echo -e "  🟢 ONLINE : $online_count"
echo -e "  🔴 OFFLINE : $offline_count"
echo -e "==============================="

