"""Endpoint /metrics minimal, partage par les services NeronOS.

Expose les collecteurs par defaut de prometheus_client (process_*, python_*)
plus quelques gauges de niveau processus, labellisees par service.

Les metriques de la MACHINE (cpu/ram/disque de l'hote) ne sont volontairement
pas exposees ici : elles seraient identiques pour tous les services d'un meme
hote. Elles relevent du self_model ou d'un node_exporter.

Les gauges de ce module vivent dans un registre PRIVE, pas dans le registre
par defaut. En production chaque service est un processus distinct et les deux
choix seraient equivalents, mais un seul processus peut charger plusieurs
applications Neron a la fois (suite de tests, mise au point). Or le Core
declare de son cote un `neron_process_ram_mb` non labellise : enregistrer le
notre sous le meme nom dans le registre par defaut leve alors
`Duplicated timeseries in CollectorRegistry` et rend le module inimportable.
Le registre prive supprime le conflit par construction.
"""

from __future__ import annotations

import os
import time

import psutil
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    CollectorRegistry,
    Gauge,
    generate_latest,
)

_PROC = psutil.Process(os.getpid())

_SERVICE_REGISTRY = CollectorRegistry()

_UPTIME = Gauge(
    "neron_service_uptime_seconds",
    "Uptime du processus de service",
    ["service"],
    registry=_SERVICE_REGISTRY,
)
_CPU = Gauge(
    "neron_process_cpu_percent",
    "CPU du processus de service",
    ["service"],
    registry=_SERVICE_REGISTRY,
)
_RAM = Gauge(
    "neron_process_ram_mb",
    "Memoire residente du processus de service, en Mo",
    ["service"],
    registry=_SERVICE_REGISTRY,
)


def _refresh(service: str) -> None:
    try:
        _UPTIME.labels(service=service).set(
            round(time.time() - _PROC.create_time(), 2)
        )
        # interval=None : non bloquant, delta depuis l'appel precedent
        _CPU.labels(service=service).set(_PROC.cpu_percent(interval=None))
        _RAM.labels(service=service).set(
            round(_PROC.memory_info().rss / 1024 / 1024, 1)
        )
    except psutil.Error:
        pass


def export(service: str) -> str:
    _refresh(service)
    default = generate_latest(REGISTRY).decode("utf-8")
    own = generate_latest(_SERVICE_REGISTRY).decode("utf-8")
    return default + own


def mount_metrics(app, service: str) -> None:
    """Declare la route GET /metrics sur l'application donnee."""

    from fastapi import Response

    @app.get("/metrics")
    def prometheus_metrics() -> Response:
        return Response(
            content=export(service),
            media_type=CONTENT_TYPE_LATEST,
        )
