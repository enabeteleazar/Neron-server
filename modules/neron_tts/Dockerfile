FROM python:3.11-slim

LABEL maintainer="Neron AI Team"
LABEL version="1.0.0"
LABEL description="Service TTS pyttsx3 - Neron AI"

WORKDIR /app

RUN apt-get update && apt-get install -y \
    espeak \
    espeak-ng \
    libespeak-ng-dev \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY engine.py .
COPY app.py .

ENV PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO \
    TTS_ENGINE=pyttsx3 \
    TTS_LANGUAGE=fr \
    TTS_RATE=150 \
    TTS_VOLUME=1.0 \
    TTS_MAX_CHARS=1000

RUN useradd -m -u 1000 neron && chown -R neron:neron /app
USER neron

EXPOSE 8003

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8003"]
