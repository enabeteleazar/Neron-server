# app/fixer.py
# Autocorrection intelligente : restart services, retry, validation post-fix

import subprocess
import time
from typing import Any
from doctor.config import cfg
from doctor.logger import get_logger
from doctor.monitor import get_service_status

log = get_logger("doctor.fixer")


# ─────────────────────────────────────────────
#  Restart d'un service avec retry + validation
# ─────────────────────────────────────────────

def restart_service(service: str) -> dict[str, Any]:
    """
    Tente de redémarrer un service systemd.
    Réessaie jusqu'à cfg.FIX_RETRY_COUNT fois avec délai.
    Valide l'état après chaque tentative.
    """
    log.info(f"Attempting restart of service: {service}")

    result: dict[str, Any] = {
        "service": service,
        "action": "restart",
        "attempts": [],
        "success": False,
        "final_state": None,
    }

    for attempt in range(1, cfg.FIX_RETRY_COUNT + 1):
        log.debug(f"  attempt {attempt}/{cfg.FIX_RETRY_COUNT}")
        attempt_info: dict[str, Any] = {"attempt": attempt}

        try:
            proc = subprocess.run(
                ["systemctl", "restart", service],
                capture_output=True, text=True, timeout=30
            )
            attempt_info["returncode"] = proc.returncode
            attempt_info["stderr"]     = proc.stderr.strip() or None

            if proc.returncode != 0:
                attempt_info["error"] = f"systemctl returned {proc.returncode}"
                log.warning(f"  restart failed (rc={proc.returncode}): {proc.stderr.strip()}")
            else:
                # Délai pour laisser le service démarrer
                time.sleep(cfg.FIX_RETRY_DELAY)

                # Validation
                status = get_service_status(service)
                attempt_info["post_status"] = status["state"]

                if status["active"]:
                    attempt_info["success"] = True
                    result["success"] = True
                    result["final_state"] = status["state"]
                    log.info(f"  service {service} is now active (attempt {attempt})")
                    result["attempts"].append(attempt_info)
                    return result
                else:
                    attempt_info["success"] = False
                    attempt_info["error"] = f"Service still {status['state']} after restart"
                    log.warning(f"  service still {status['state']} after attempt {attempt}")

        except subprocess.TimeoutExpired:
            attempt_info["error"] = "systemctl restart timed out"
            log.error(f"  restart timed out for {service}")
        except FileNotFoundError:
            attempt_info["error"] = "systemctl not available"
            log.error("  systemctl not found — not a systemd system?")
            result["attempts"].append(attempt_info)
            return result
        except Exception as e:
            attempt_info["error"] = str(e)
            log.error(f"  unexpected error: {e}")

        result["attempts"].append(attempt_info)

        if attempt < cfg.FIX_RETRY_COUNT:
            log.debug(f"  waiting {cfg.FIX_RETRY_DELAY}s before next attempt...")
            time.sleep(cfg.FIX_RETRY_DELAY)

    # Toutes les tentatives épuisées
    final = get_service_status(service)
    result["final_state"] = final["state"]
    log.error(f"Failed to restart {service} after {cfg.FIX_RETRY_COUNT} attempts")
    return result


# ─────────────────────────────────────────────
#  Orchestration des fixes
# ─────────────────────────────────────────────

def apply_fixes(report: dict) -> dict[str, Any]:
    """
    Analyse le rapport de diagnostic et applique les corrections nécessaires.
    Retourne un dict détaillé de toutes les actions effectuées.
    """
    fixes: dict[str, Any] = {
        "actions": [],
        "services_restarted": [],
        "services_failed": [],
        "total_fixes_attempted": 0,
        "total_fixes_succeeded": 0,
    }

    http_tests = report.get("tests", {})
    services   = report.get("services", {})

    # Détermine quels services nécessitent un redémarrage
    services_to_restart: set[str] = set()

    # Via les tests HTTP
    for test_name, test_result in http_tests.items():
        if test_name.startswith("_"):
            continue
        if isinstance(test_result, dict) and not test_result.get("ok", True):
            # Mapping test → service systemd
            service_map = {
                "server_health": "neron-server",
                "server_status": "neron-server",
                "llm_health":    "neron-llm",
                "ollama":        "ollama",
            }
            svc = service_map.get(test_name)
            if svc and svc in cfg.SYSTEMD_SERVICES:
                services_to_restart.add(svc)

    # Via les états systemd
    for svc_name, svc_info in services.items():
        if isinstance(svc_info, dict) and not svc_info.get("active", True):
            services_to_restart.add(svc_name)

    if not services_to_restart:
        log.info("No fixes needed — all services appear healthy")
        fixes["message"] = "No fixes needed"
        return fixes

    # Application des fixes
    for service in services_to_restart:
        fixes["total_fixes_attempted"] += 1
        log.info(f"Fixing: {service}")

        fix_result = restart_service(service)
        fixes["actions"].append(fix_result)

        if fix_result["success"]:
            fixes["services_restarted"].append(service)
            fixes["total_fixes_succeeded"] += 1
        else:
            fixes["services_failed"].append(service)

    fixes["fix_rate"] = (
        round(fixes["total_fixes_succeeded"] / fixes["total_fixes_attempted"] * 100)
        if fixes["total_fixes_attempted"] else 100
    )

    log.info(
        f"Fixes complete: {fixes['total_fixes_succeeded']}/{fixes['total_fixes_attempted']} succeeded"
    )
    return fixes
