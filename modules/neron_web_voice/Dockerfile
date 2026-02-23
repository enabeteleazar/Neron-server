# Image officielle Node.js
FROM node:20-slim

# Définition du dossier de travail
WORKDIR /app

# Copier uniquement les fichiers nécessaires à l'installation
COPY package*.json ./

# Installation des dépendances en mode production
RUN npm install --omit=dev

# Copier le reste de l'application
COPY server ./server
COPY public ./public

# Variable d'environnement production
ENV NODE_ENV=production

# Exposition du port
EXPOSE 8080

# Commande de démarrage
CMD ["node", "server/index.js"]
