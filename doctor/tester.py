# app/tester.py
# test runtime

import requests


def test_services():
    results = {}

    # SERVER TESTS
    try:
        r = requests.get("http://localhost:8010/health", timeout=3)
        results["server_health"] = r.status_code
    except Exception as e:
        results["server_health"] = str(e)

    try:
        r = requests.get("http://localhost:8010/status", timeout=3)
        results["server_status"] = r.status_code
    except Exception as e:
        results["server_status"] = str(e)

    # LLM TESTS
    try:
        r = requests.get("http://localhost:8765/llm/health", timeout=3)
        results["llm_health"] = r.status_code
    except Exception as e:
        results["llm_health"] = str(e)

    return results
