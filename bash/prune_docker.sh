#!/bin/bash

echo -e "\033[1;31mATTENTION : Cette opération va SUPPRIMER tous les containers, images, caches et volumes inutilisés.\033[0m"
read -p "Voulez-vous continuer ? (yes/no) : " choice

if [[ "$choice" != "yes" ]]; then
    echo "Opération annulée."
    exit 1
fi

echo -e "\033[1;33m[HOMEBOX] Nettoyage complet de Docker...\033[0m"

docker stop $(docker ps -aq)
docker rm -f $(docker ps -aq)
docker rmi -f $(docker images -q)
docker system prune -af --volumes

echo -e "\033[1;32m✔ Docker a été entièrement nettoyé.\033[0m"
