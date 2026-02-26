FROM python:3.12-slim

# Métadonnées
LABEL maintainer="enabeteleazar"
LABEL description="Homebox Control Plane - Service Monitoring"

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Créer un utilisateur non-root
RUN useradd -m -u 1000 controlplane && \
    mkdir -p /app/data /app/logs && \
    chown -R controlplane:controlplane /app

# Définir le répertoire de travail
WORKDIR /app

# Copier les requirements en premier (pour le cache Docker)
COPY --chown=controlplane:controlplane requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code de l'application
COPY --chown=controlplane:controlplane . .

# Donner les permissions nécessaires
RUN chmod +x app.py && \
    chown -R controlplane:controlplane /app/data /app/logs

# Utiliser l'utilisateur non-root
USER controlplane

# Healthcheck
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python3 -c "import sys; sys.exit(0)" || exit 1

# Volume pour la persistance
VOLUME ["/app/data", "/app/logs"]

# Commande par défaut
CMD ["python3", "app.py"]
