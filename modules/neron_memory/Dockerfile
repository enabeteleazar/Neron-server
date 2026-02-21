# modules/neron_memory/Dockerfile

# Builder stage
FROM python:3.11-slim AS builder

WORKDIR /install

# Installer outils nécessaires pour builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copier et installer les dépendances Python dans /install
COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

# Stage final
FROM python:3.11-slim

WORKDIR /app

# Installer outils runtime minimum
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copier les packages Python installés depuis le builder
COPY --from=builder /install /usr/local

# Copier le code de l'application
COPY app.py .

# Exposer le port du service
EXPOSE 8002

# Lancer l'application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8002", "--log-level", "info"]
