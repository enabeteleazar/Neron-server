# ---------- Builder Stage ----------
FROM python:3.11-slim AS builder

LABEL maintainer="Néron AI Team"
LABEL description="Service wrapper HTTP pour Ollama - Néron AI Assistant"
LABEL version="1.0.0"

WORKDIR /install

# Installer outils système nécessaires pour pip et compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copier et installer les dépendances Python dans un prefix isolé
COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

# ---------- Runtime Stage ----------
FROM python:3.11-slim

WORKDIR /app

# Installer seulement ce qui est nécessaire pour runtime
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copier les dépendances Python depuis le builder
COPY --from=builder /install /usr/local

# Copier le code de l'application
COPY config.py .
COPY models.py .
COPY ollama_client.py .
COPY app.py .
COPY __init__.py .

# Variables d'environnement par défaut
ENV PYTHONUNBUFFERED=1 \
    ENV=production \
    LOG_LEVEL=INFO \
    SERVICE_HOST=0.0.0.0 \
    SERVICE_PORT=5000 \
    OLLAMA_HOST=http://neron_ollama:11434 \
    OLLAMA_TIMEOUT=300.0 \
    DEFAULT_MODEL=llama3.2:1b \
    MAX_TOKENS=2048 \
    TEMPERATURE=0.7

# Créer un utilisateur non-root
RUN useradd -m -u 1000 neron && chown -R neron:neron /app
USER neron

# Exposer le port du service
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Démarrer l'application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000", "--log-level", "info"]
