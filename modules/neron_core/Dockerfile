# === Étape 1 : Builder ===
FROM python:3.11-slim AS builder

# Installer dépendances système nécessaires pour pip / compilation
RUN apt update && apt install -y ffmpeg git curl build-essential && apt clean && rm -rf /var/lib/apt/lists/*

WORKDIR /install

# Copier et installer les dépendances Python
COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

# === Étape 2 : Image finale ===
FROM python:3.11-slim

# Installer dépendances système nécessaires à l’exécution
RUN apt update && apt install -y ffmpeg git curl && apt clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copier uniquement les dépendances Python depuis l'étape builder
COPY --from=builder /install /usr/local

# Copier le code de l'application
COPY app.py .
COPY __init__.py .
COPY agents/ ./agents/
COPY orchestrator/ ./orchestrator/
COPY neron_time/ ./neron_time/

# Créer un utilisateur non-root
RUN useradd -m -u 1000 neron && chown -R neron:neron /app
USER neron

# Exposer le port STT
EXPOSE 8000

# Commande pour lancer l'API
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
