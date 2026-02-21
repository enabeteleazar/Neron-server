FROM python:3.11-slim

LABEL maintainer="Neron AI Team"
LABEL version="1.1.0"

WORKDIR /app

RUN apt-get update && apt-get install -y ffmpeg curl && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY download_model.py .
ARG WHISPER_MODEL=base
ENV WHISPER_MODEL=${WHISPER_MODEL}
RUN python3 download_model.py

COPY app.py .

ENV PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO \
    WHISPER_DOWNLOAD_ROOT=/app/models \
    AUDIO_MAX_SIZE_MB=10

RUN useradd -m -u 1000 neron && chown -R neron:neron /app
USER neron

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=15s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
