# modules/neron_web/Dockerfile

# Builder stage
FROM python:3.11-slim AS builder

WORKDIR /install

# Installer pip et dépendances système minimum pour builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copier et installer les dépendances Python dans /install
COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

# Stage final
FROM python:3.11-slim

WORKDIR /app

# Installer runtime minimal
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copier les packages Python installés depuis le builder
COPY --from=builder /install /usr/local

# Copier le code de l'application
COPY app.py .

# Exposer le port du service
EXPOSE 7860

# Lancer l'application
CMD ["python", "app.py"]
