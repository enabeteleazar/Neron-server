"""La route /metrics partagee ne doit pas casser la generation du schema.

`mount_metrics` importe `Response` DANS la fonction, pour ne pas imposer
fastapi a l'import du module. L'annotation `-> Response` du handler etait
donc introuvable dans les globals du module, ou FastAPI resout les
annotations : `GET /openapi.json` renvoyait 500 sur tous les services montant
cette route — llm, memory et goal. Core, qui n'utilise pas ce squelette,
n'etait pas touche, ce qui a fait passer le defaut pour un probleme de Goal.

Ce test verrouille le socle lui-meme, pas chaque service : c'est la ou le
defaut vivait.
"""

from __future__ import annotations

from fastapi import FastAPI

from server.common.metrics import mount_metrics


def test_mounted_metrics_route_keeps_openapi_generatable():
    app = FastAPI()
    mount_metrics(app, "test-service")

    schema = app.openapi()

    assert "/metrics" in schema["paths"]


def test_metrics_route_answers():
    from fastapi.testclient import TestClient

    app = FastAPI()
    mount_metrics(app, "test-service")

    response = TestClient(app).get("/metrics")

    assert response.status_code == 200
    assert "python_info" in response.text or "process_" in response.text
