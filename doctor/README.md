# Neron Doctor v2

Agent de diagnostic et d'autocorrection pour l'infrastructure Néron.
Tourne en microservice FastAPI indépendant sur le homebox.

---

## Architecture

```
app/
├── main.py       # FastAPI — routing des endpoints
├── config.py     # Config centralisée via .env
├── auth.py       # Auth par API Key (header X-Doctor-Key)
├── logger.py     # Logger centralisé avec rotation fichiers
├── runner.py     # Orchestrateur — pipeline 5 phases + streaming SSE
├── analyzer.py   # Analyse statique AST (syntaxe, imports, patterns)
├── monitor.py    # Métriques système (psutil) + journalctl
├── tester.py     # Tests HTTP endpoints (status codes + latence)
└── fixer.py      # Autocorrection systemd avec retry + validation
```

---

## Pipeline de diagnostic (5 phases)

```
POST /diagnose
     │
     ├─ PHASE 1  Métriques système (CPU, RAM, disque) + état services systemd
     ├─ PHASE 2  Analyse statique AST des projets (syntax, imports, patterns)
     ├─ PHASE 3  Analyse logs journalctl (erreurs, warnings)
     ├─ PHASE 4  Tests HTTP endpoints (health, status, LLM, Ollama)
     └─ PHASE 5  Autocorrection (restart services KO) + re-test final
                        └─ Verdict global (score 0-100, status, résumé)
```

---

## Endpoints

| Méthode | Endpoint         | Description                                      |
|---------|------------------|--------------------------------------------------|
| GET     | `/`              | Healthcheck de Doctor lui-même                   |
| POST    | `/diagnose`      | Pipeline complet (bloquant, rapport JSON)        |
| GET     | `/stream`        | Diagnostic en streaming SSE (phase par phase)    |
| GET     | `/status`        | Snapshot rapide (système + services + HTTP)      |
| GET     | `/analyze`       | Analyse statique AST uniquement                  |
| GET     | `/logs`          | Logs journalctl des services                     |
| POST    | `/fix/{service}` | Redémarre manuellement un service                |
| GET     | `/config`        | Config active (clé API masquée)                  |

---

## Installation

```bash
git clone https://github.com/enabeteleazar/Neron-doctor.git
cd Neron-doctor
cp .env.example .env
# Éditer .env selon l'environnement

pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8090 --reload
```

Documentation interactive disponible sur `http://localhost:8090/docs`

---

## Déploiement systemd

Créer `/etc/systemd/system/neron-doctor.service` :

```ini
[Unit]
Description=Neron Doctor Agent
After=network.target

[Service]
User=root
WorkingDirectory=/etc/neron/doctor
EnvironmentFile=/etc/neron/doctor/.env
ExecStart=/usr/bin/uvicorn app.main:app --host 0.0.0.0 --port 8090
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable --now neron-doctor
```

---

## Authentification

Définir `DOCTOR_API_KEY` dans `.env`.  
Passer le header `X-Doctor-Key: <valeur>` sur tous les appels.  
Si la variable est vide → auth désactivée (mode dev).

---

## Streaming SSE

```javascript
const source = new EventSource("http://homebox:8090/stream");
source.onmessage = (e) => {
  const { phase, data } = JSON.parse(e.data);
  console.log(phase, data);
};
```

Phases émises : `start` → `system` → `services` → `analysis`
→ `logs` → `tests` → `fixes` → `final_tests` → `verdict` → `done`
