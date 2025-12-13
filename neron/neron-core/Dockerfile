# Image de base Python (3.11 slim pour légèreté)
FROM python:3.11-slim

# Définir le répertoire de travail dans le container
WORKDIR /app

# Copier les fichiers nécessaires dans le container
COPY requirements.txt .
COPY . .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Exposer le port de l'API Nerón-core
EXPOSE 4000

# Définir la commande par défaut pour démarrer Nerón-core
CMD ["python", "main.py"]

