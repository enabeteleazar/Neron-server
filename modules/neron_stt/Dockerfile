modules/neron_stt/Dockerfile

# Builder stage
FROM python:3.11-slim AS builder

WORKDIR /install

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --prefix=/install --no-cache-dir -r requirements.txt


# ===== Runtime stage =====
FROM python:3.11-slim

WORKDIR /app

# Installer uniquement ffmpeg (pas build-essential)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl && \
    rm -rf /var/lib/apt/lists/*

# Copier les dépendances installées
COPY --from=builder /install /usr/local

# Copier le code
COPY app.py .
COPY download_model.py .

ENV PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO \
    WHISPER_DOWNLOAD_ROOT=/app/models \
    AUDIO_MAX_SIZE_MB=10

RUN useradd -m -u 1000 neron && chown -R neron:neron /app
USER neron

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=15s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["python3", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
