# app/runner.py
# Orchestrateur principal — pipeline de diagnostic en 5 phases

import time
from datetime import datetime, timezone
from typing import Any, Generator

from doctor.config import cfg
from doctor.logger import get_logger
from doctor.analyzer import analyze_project
from doctor.tester import test_services
from doctor.fixer import apply_fixes
from doctor.monitor import get_system_metrics, get_all_services_status, get_all_journal_errors

log = get_logger("doctor.runner")


def build_report_skeleton() -> dict[str, Any]:
    return {
        "meta": {
            "version": "2.0.0",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
            "duration_s": None,
        },
        "system": {},
        "services": {},
        "analysis": {},
        "logs": {},
        "tests": {},
        "fixes": {},
        "final_tests": {},
        "verdict": {
            "status": "unknown",
            "score": 0,
            "issues_count": 0,
            "fixed_count": 0,
            "summary": "",
        },
    }


def run_full_diagnosis() -> dict[str, Any]:
    """
    Pipeline complet en 5 phases :
      1. Métriques système & état des services
      2. Analyse statique des projets (AST)
      3. Analyse des logs journalctl
      4. Tests HTTP des endpoints
      5. Autocorrection + re-test final
    """
    t0 = time.time()
    log.info("=" * 60)
    log.info("Starting Neron Doctor — full diagnosis")
    log.info("=" * 60)

    report = build_report_skeleton()

    # ── PHASE 1 : Système & services ──────────────────────────
    log.info("[1/5] System metrics & service status")
    report["system"]   = get_system_metrics()
    report["services"] = get_all_services_status()

    # ── PHASE 2 : Analyse statique ────────────────────────────
    log.info("[2/5] Static analysis")
    report["analysis"]["server"] = analyze_project(cfg.SERVER_PATH)
    report["analysis"]["llm"]    = analyze_project(cfg.LLM_PATH)

    # ── PHASE 3 : Logs journalctl ─────────────────────────────
    log.info("[3/5] Journal log analysis")
    report["logs"] = get_all_journal_errors()

    # ── PHASE 4 : Tests HTTP ──────────────────────────────────
    log.info("[4/5] HTTP endpoint tests")
    report["tests"] = test_services()

    # ── PHASE 5 : Fixes + re-test ─────────────────────────────
    log.info("[5/5] Apply fixes & re-test")
    report["fixes"] = apply_fixes(report)

    if report["fixes"].get("total_fixes_attempted", 0) > 0:
        log.info("Re-testing after fixes...")
        report["final_tests"] = test_services()
    else:
        report["final_tests"] = report["tests"]

    # ── Verdict final ─────────────────────────────────────────
    report["verdict"] = _compute_verdict(report)

    elapsed = round(time.time() - t0, 2)
    report["meta"]["finished_at"] = datetime.now(timezone.utc).isoformat()
    report["meta"]["duration_s"]  = elapsed

    log.info(f"Diagnosis complete in {elapsed}s — status: {report['verdict']['status']}")
    return report


def _compute_verdict(report: dict) -> dict[str, Any]:
    """Calcule un verdict global pondéré."""
    issues = 0
    fixed  = report.get("fixes", {}).get("total_fixes_succeeded", 0)

    # Compte les issues des analyses
    for proj in report.get("analysis", {}).values():
        issues += len(proj.get("issues", []))
        issues += len(proj.get("syntax_errors", []))

    # Issues HTTP
    tests = report.get("final_tests", {})
    failed_http = tests.get("_summary", {}).get("failed", 0)
    issues += failed_http

    # Issues système
    sys_status = report.get("system", {}).get("global_status", "ok")
    if sys_status == "warn":
        issues += 1

    # Services down
    services_down = sum(
        1 for s in report.get("services", {}).values()
        if isinstance(s, dict) and not s.get("active", True)
    )
    issues += services_down

    # Calcul du score (0-100)
    total_checks = max(1, issues + fixed + 5)  # 5 checks minimum de base
    score = max(0, min(100, round((1 - issues / total_checks) * 100)))

    if issues == 0:
        status  = "healthy"
        summary = "All systems operational."
    elif fixed >= issues:
        status  = "recovered"
        summary = f"{fixed} issue(s) detected and fixed automatically."
    elif failed_http > 0 or services_down > 0:
        status  = "degraded"
        summary = f"{issues} issue(s) remaining. Manual intervention may be needed."
    else:
        status  = "warning"
        summary = f"{issues} non-critical issue(s) found."

    return {
        "status":       status,
        "score":        score,
        "issues_count": issues,
        "fixed_count":  fixed,
        "summary":      summary,
    }


# ─────────────────────────────────────────────
#  Streaming (SSE generator)
# ─────────────────────────────────────────────

def run_diagnosis_streaming() -> Generator[str, None, None]:
    """
    Version streaming du diagnostic.
    Yield des événements SSE au fur et à mesure des phases.
    """
    import json

    def event(phase: str, data: Any) -> str:
        payload = json.dumps({"phase": phase, "data": data}, default=str)
        return f"data: {payload}\n\n"

    t0 = time.time()
    report = build_report_skeleton()

    yield event("start", {"message": "Neron Doctor starting...", "version": "2.0.0"})

    # Phase 1
    yield event("phase", {"step": 1, "name": "system_metrics"})
    report["system"]   = get_system_metrics()
    report["services"] = get_all_services_status()
    yield event("system",   report["system"])
    yield event("services", report["services"])

    # Phase 2
    yield event("phase", {"step": 2, "name": "static_analysis"})
    report["analysis"]["server"] = analyze_project(cfg.SERVER_PATH)
    report["analysis"]["llm"]    = analyze_project(cfg.LLM_PATH)
    yield event("analysis", report["analysis"])

    # Phase 3
    yield event("phase", {"step": 3, "name": "log_analysis"})
    report["logs"] = get_all_journal_errors()
    yield event("logs", report["logs"])

    # Phase 4
    yield event("phase", {"step": 4, "name": "http_tests"})
    report["tests"] = test_services()
    yield event("tests", report["tests"])

    # Phase 5
    yield event("phase", {"step": 5, "name": "fixes"})
    report["fixes"] = apply_fixes(report)
    if report["fixes"].get("total_fixes_attempted", 0) > 0:
        report["final_tests"] = test_services()
    else:
        report["final_tests"] = report["tests"]
    yield event("fixes",       report["fixes"])
    yield event("final_tests", report["final_tests"])

    # Verdict
    report["verdict"]             = _compute_verdict(report)
    report["meta"]["finished_at"] = datetime.now(timezone.utc).isoformat()
    report["meta"]["duration_s"]  = round(time.time() - t0, 2)
    yield event("verdict", report["verdict"])
    yield event("done",    {"duration_s": report["meta"]["duration_s"]})
