# Stage 1 : build et téléchargement du modèle
FROM python:3.11-slim AS builder
WORKDIR /app

# Installer dépendances système minimales
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl && \
    rm -rf /var/lib/apt/lists/*

# Installer pip et dépendances Python
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Télécharger le modèle Whisper
COPY download_model.py .
ARG WHISPER_MODEL=base
ENV WHISPER_MODEL=${WHISPER_MODEL}
RUN python3 download_model.py --compute-type int8

# Stage 2 : image finale
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /app /app
COPY app.py .

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO \
    WHISPER_DOWNLOAD_ROOT=/app/models \
    AUDIO_MAX_SIZE_MB=10 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1

# Ajouter un utilisateur non-root
RUN useradd -m -u 1000 neron && chown -R neron:neron /app
USER neron

EXPOSE 8001

# Healthcheck
HEALTHCHECK --interval=30s --timeout=15s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Lancer le service
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
