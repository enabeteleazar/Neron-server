# app/tester.py
# Tests runtime HTTP — vérification status codes, latence, contenu

import time
import requests
from typing import Any
from doctor.config import cfg
from doctor.logger import get_logger

log = get_logger("doctor.tester")


# ─────────────────────────────────────────────
#  Test HTTP unitaire
# ─────────────────────────────────────────────

def _test_endpoint(name: str, url: str, expected_status: int = 200) -> dict[str, Any]:
    log.debug(f"Testing {name}: {url}")
    start = time.time()

    try:
        r = requests.get(url, timeout=cfg.HTTP_TIMEOUT)
        latency_ms = round((time.time() - start) * 1000)
        ok = r.status_code == expected_status

        result = {
            "name": name,
            "url": url,
            "status_code": r.status_code,
            "latency_ms": latency_ms,
            "ok": ok,
            "status": "ok" if ok else "error",
            "error": None,
        }

        if not ok:
            result["error"] = f"Expected {expected_status}, got {r.status_code}"
            log.warning(f"{name} returned {r.status_code} (expected {expected_status})")
        else:
            log.debug(f"{name} OK ({latency_ms}ms)")

        # Tentative de lecture JSON si disponible
        try:
            result["body"] = r.json()
        except Exception:
            result["body"] = r.text[:200] if r.text else None

        return result

    except requests.exceptions.ConnectionError:
        err = f"Connection refused to {url}"
    except requests.exceptions.Timeout:
        err = f"Timeout after {cfg.HTTP_TIMEOUT}s"
    except Exception as e:
        err = str(e)

    log.error(f"{name} FAILED: {err}")
    return {
        "name": name,
        "url": url,
        "status_code": None,
        "latency_ms": round((time.time() - start) * 1000),
        "ok": False,
        "status": "error",
        "error": err,
        "body": None,
    }


# ─────────────────────────────────────────────
#  Suite de tests complète
# ─────────────────────────────────────────────

def test_services() -> dict[str, Any]:
    log.info("Running HTTP service tests")

    endpoints = [
        ("server_health",  cfg.SERVER_HEALTH_URL,  200),
        ("server_status",  cfg.SERVER_STATUS_URL,  200),
        ("llm_health",     cfg.LLM_HEALTH_URL,     200),
        ("ollama",         cfg.OLLAMA_URL,          200),
    ]

    results = {}
    for name, url, expected in endpoints:
        results[name] = _test_endpoint(name, url, expected)

    # Score global
    total = len(results)
    passed = sum(1 for r in results.values() if r["ok"])

    results["_summary"] = {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "score_percent": round((passed / total) * 100) if total else 0,
        "global_status": "ok" if passed == total else ("warn" if passed > 0 else "error"),
    }

    log.info(
        f"HTTP tests: {passed}/{total} passed "
        f"({results['_summary']['score_percent']}%)"
    )
    return results
