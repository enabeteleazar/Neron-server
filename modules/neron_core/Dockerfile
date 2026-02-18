FROM python:3.11

# installer les dépendantes systeme
RUN apt update && apt install -y ffmpeg git curl && apt clean

# Definit le répertoire de travail
WORKDIR /app

# Copier les fichers de requirements et installer 
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code de l'application
COPY app.py .
COPY agents/ ./agents/
COPY orchestrator/ ./orchestrator/

# exposer le port STT
EXPOSE 8000

# Commande pour lancer l'API
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

