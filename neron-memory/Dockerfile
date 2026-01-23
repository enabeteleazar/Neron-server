FROM python:3.10-slim

# installer les dépendantes systeme
RUN apt update && apt install -y ffmpeg git curl && apt clean

# Definit le répertoire de travail
WORKDIR /app

# Copier les fichers de requirements et installer 
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code de l'application
COPY app.py .

# exposer le port STT
EXPOSE 8002

# Commande pour lancer l'API
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8002"]
