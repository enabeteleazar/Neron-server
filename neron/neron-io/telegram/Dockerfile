# Image de base Python
FROM python:3.11-slim

WORKDIR /app

# Copier les fichiers nécessaires
COPY requirements.txt .
COPY . .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Exposer un port si nécessaire (optionnel)
EXPOSE 5001

# Commande pour lancer le bot
CMD ["python", "bot.py"]

