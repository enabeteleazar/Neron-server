FROM python:3.11-slim

WORKDIR /app

# Dépendances système
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl && \
    rm -rf /var/lib/apt/lists/*

# Copier requirements et installer **avant** de changer d'utilisateur
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copier le code
COPY download_model.py .
COPY app.py .

# Définir variables
ENV PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO \
    WHISPER_DOWNLOAD_ROOT=/app/models \
    AUDIO_MAX_SIZE_MB=10 \
    PATH="/usr/local/bin:$PATH"

ARG WHISPER_MODEL=base
ENV WHISPER_MODEL=${WHISPER_MODEL}
RUN python3 download_model.py

# Créer l'utilisateur neron et changer les permissions
RUN useradd -m -u 1000 neron && chown -R neron:neron /app
USER neron

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=15s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Utiliser python -m uvicorn pour s'assurer que le binaire est trouvé
CMD ["python3", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
