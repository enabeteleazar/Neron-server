FROM python:3.11-slim

LABEL maintainer="Neron AI Team"
LABEL version="1.0.0"

WORKDIR /app

RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip && \
    pip install setuptools wheel && \
    pip install torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Telecharger le modele Whisper dans /app/models (accessible par user neron)
ARG WHISPER_MODEL=base
ENV WHISPER_DOWNLOAD_ROOT=/app/models
RUN python3 -c "import whisper; whisper.load_model('${WHISPER_MODEL}', download_root='/app/models')"

COPY app.py .

ENV PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO \
    WHISPER_MODEL=base \
    WHISPER_DOWNLOAD_ROOT=/app/models

# Utilisateur non-root avec acces a /app
RUN useradd -m -u 1000 neron && chown -R neron:neron /app
USER neron

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=15s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
