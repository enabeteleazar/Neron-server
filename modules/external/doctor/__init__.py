"""Doctor integration (health / diagnostics)
Façade vers les scripts doctor existants.
"""

def run_diagnostics():
    try:
        from server.core.scripts.doctor import run as _run
        return _run()
    except Exception:
        return {"status": "unavailable"}
