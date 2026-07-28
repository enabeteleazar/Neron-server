"""Endpoint /metrics minimal, partage par les services NeronOS.

Expose les collecteurs par defaut de prometheus_client (process_*, python_*)
plus quelques gauges de niveau processus, labellisees par service.

Les metriques de la MACHINE (cpu/ram/disque de l'hote) ne sont volontairement
pas exposees ici : elles seraient identiques pour tous les services d'un meme
hote. Elles relevent du self_model ou d'un node_exporter.
"""

from __future__ import annotations

import os
import time

import psutil
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    Gauge,
    generate_latest,
)

_PROC = psutil.Process(os.getpid())

_UPTIME = Gauge(
    "neron_service_uptime_seconds",
    "Uptime du processus de service",
    ["service"],
)
_CPU = Gauge(
    "neron_process_cpu_percent",
    "CPU du processus de service",
    ["service"],
)
_RAM = Gauge(
    "neron_process_ram_mb",
    "Memoire residente du processus de service, en Mo",
    ["service"],
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
    return generate_latest(REGISTRY).decode("utf-8")


def mount_metrics(app, service: str) -> None:
    """Declare la route GET /metrics sur l'application donnee."""

    from fastapi import Response

    @app.get("/metrics")
    def prometheus_metrics() -> Response:
        return Response(
            content=export(service),
            media_type=CONTENT_TYPE_LATEST,
        )
