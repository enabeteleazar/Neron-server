#!/bin/bash 

echo -e "\033[1;34m[HOMEBOX] Vérification de l'état des services...\033[0m" 
services=(
"portainer"
"nginx-proxy"
"cadvisor"
"prometheus"
"grafana"
"homeassistant"
"telegram-bot"
"ollama"
"llm-api"
"codi-tv-backend"
"codi-tv-frontend"
"neo-homebox-ui-backend"
"neo-homebox-ui-frontend"
"dashboard-frontend"
"dashboard-backend"
)
for s in "${services[@]}";
do status=$(docker ps --filter "name=$s" --format "{{.Status}}")

if [[ -z "$status" ]];

then
  echo -e "🔴 \033[1;31m$s : OFFLINE\033[0m"
else
  echo -e "🟢 \033[1;32m$s : $status\033[0m" 
fi 
done
