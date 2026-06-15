# doctor/tester.py
# Tests runtime — vérifie la disponibilité des endpoints HTTP

import requests
from doctor.config import cfg
from doctor.logger import get_logger

log = get_logger("doctor.tester")


def test_services() -> dict:
    results = {}

    def _get(key: str, url: str) -> None:
        try:
            r = requests.get(url, timeout=cfg.HTTP_TIMEOUT)
            results[key] = r.status_code
            log.debug("%s → %s %d", key, url, r.status_code)
        except Exception as e:
            results[key] = str(e)
            log.warning("%s → %s FAILED: %s", key, url, e)

    _get("server_health", cfg.SERVER_HEALTH_URL)
    _get("server_status", cfg.SERVER_STATUS_URL)
    _get("llm_health",    cfg.LLM_HEALTH_URL)

    return results
