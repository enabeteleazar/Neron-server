FROM python:3.12-slim

# Installer gcc, build-essential pour psutil si nécessaire
RUN apt-get update && apt-get install -y gcc python3-dev libffi-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copier les requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier tout le backend
COPY . .

# Définir PYTHONPATH pour que Python trouve api/
ENV PYTHONPATH=/app

# Lancer uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]
