# app/main.py
# FastAPI — Neron Doctor v2
# Endpoints : /diagnose, /status, /analyze, /logs, /fix, /stream

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from datetime import datetime, timezone

from doctor.auth import require_api_key
from doctor.config import cfg
from doctor.logger import get_logger
from doctor.monitor import get_system_metrics, get_all_services_status, get_all_journal_errors
from doctor.tester import test_services
from doctor.fixer import apply_fixes, restart_service
from doctor.runner import run_full_diagnosis, run_diagnosis_streaming

log = get_logger("doctor.api")

app = FastAPI(
    title="Neron Doctor",
    description="Agent de diagnostic et d'autocorrection pour l'infrastructure Néron",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────
#  ROOT — healthcheck de Doctor lui-même
# ──────────────────────────────────────────────

@app.get("/", tags=["meta"])
def root():
    return {
        "name": "Neron Doctor",
        "version": "2.0.0",
        "status": "running",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ──────────────────────────────────────────────
#  DIAGNOSE — pipeline complet (bloquant)
# ──────────────────────────────────────────────

@app.post("/diagnose", tags=["diagnosis"], dependencies=[Depends(require_api_key)])
def diagnose():
    """
    Lance le diagnostic complet en 5 phases et retourne le rapport JSON.
    Bloquant — peut prendre quelques secondes.
    """
    log.info("POST /diagnose called")
    result = run_full_diagnosis()
    return result


# ──────────────────────────────────────────────
#  STREAM — diagnostic en Server-Sent Events
# ──────────────────────────────────────────────

@app.get("/stream", tags=["diagnosis"], dependencies=[Depends(require_api_key)])
def stream_diagnosis():
    """
    Diagnostic en streaming SSE — phases envoyées au fur et à mesure.
    Connecte-toi avec EventSource côté client.
    """
    log.info("GET /stream called")
    return StreamingResponse(
        run_diagnosis_streaming(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ──────────────────────────────────────────────
#  STATUS — snapshot rapide (sans analyse AST)
# ──────────────────────────────────────────────

@app.get("/status", tags=["status"], dependencies=[Depends(require_api_key)])
def quick_status():
    """
    Snapshot rapide : système + services + tests HTTP.
    Pas d'analyse statique ni de fix.
    """
    log.info("GET /status called")
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "system":    get_system_metrics(),
        "services":  get_all_services_status(),
        "http":      test_services(),
    }


# ──────────────────────────────────────────────
#  ANALYZE — analyse statique uniquement
# ──────────────────────────────────────────────

@app.get("/analyze", tags=["analysis"], dependencies=[Depends(require_api_key)])
def analyze_only():
    """Analyse statique AST des projets — sans tests runtime ni fix."""
    from doctor.analyzer import analyze_project
    log.info("GET /analyze called")
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "server":    analyze_project(cfg.SERVER_PATH),
        "llm":       analyze_project(cfg.LLM_PATH),
    }


# ──────────────────────────────────────────────
#  LOGS — analyse des logs journalctl
# ──────────────────────────────────────────────

@app.get("/logs", tags=["logs"], dependencies=[Depends(require_api_key)])
def journal_logs():
    """Récupère et analyse les logs systemd des services Néron."""
    log.info("GET /logs called")
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "logs": get_all_journal_errors(),
    }


# ──────────────────────────────────────────────
#  FIX — déclenche les fixes sur un service donné
# ──────────────────────────────────────────────

@app.post("/fix/{service}", tags=["fix"], dependencies=[Depends(require_api_key)])
def fix_service(service: str):
    """
    Redémarre manuellement un service spécifique avec retry et validation.
    Le service doit être dans la liste SYSTEMD_SERVICES.
    """
    if service not in cfg.SYSTEMD_SERVICES:
        return JSONResponse(
            status_code=400,
            content={
                "error": f"Service '{service}' not in monitored services.",
                "allowed": cfg.SYSTEMD_SERVICES,
            },
        )
    log.info(f"POST /fix/{service} called")
    result = restart_service(service)
    return result


# ──────────────────────────────────────────────
#  CONFIG — expose la config active (sans secrets)
# ──────────────────────────────────────────────

@app.get("/config", tags=["meta"], dependencies=[Depends(require_api_key)])
def show_config():
    """Affiche la configuration active (clé API masquée)."""
    return {
        "SERVER_PATH":       cfg.SERVER_PATH,
        "LLM_PATH":          cfg.LLM_PATH,
        "LOG_DIR":           cfg.LOG_DIR,
        "SYSTEMD_SERVICES":  cfg.SYSTEMD_SERVICES,
        "HTTP_TIMEOUT":      cfg.HTTP_TIMEOUT,
        "FIX_RETRY_COUNT":   cfg.FIX_RETRY_COUNT,
        "FIX_RETRY_DELAY":   cfg.FIX_RETRY_DELAY,
        "JOURNAL_LINES":     cfg.JOURNAL_LINES,
        "CPU_WARN_PERCENT":  cfg.CPU_WARN_PERCENT,
        "MEM_WARN_PERCENT":  cfg.MEM_WARN_PERCENT,
        "DISK_WARN_PERCENT": cfg.DISK_WARN_PERCENT,
        "AUTH_ENABLED":      bool(cfg.API_KEY),
    }
