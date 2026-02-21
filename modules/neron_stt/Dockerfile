FROM python:3.11-slim

LABEL maintainer="Neron AI Team"
LABEL version="1.0.0"
LABEL description="Service STT Whisper - Neron AI"

WORKDIR /app

# Dependances systeme pour Whisper + ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Dependances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code
COPY app.py .

# Variables d environnement par defaut
ENV PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO \
    WHISPER_MODEL=base

# Utilisateur non-root
RUN useradd -m -u 1000 neron && chown -R neron:neron /app
USER neron

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=15s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
