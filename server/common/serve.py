"""Point d'entree unique des services NeronOS.

Usage : python -m common.serve <nom-du-noeud>

L'adresse et le port ne sont plus passes en argument : ils sont lus dans la
section `nodes` de neron.server.yaml, seule source de verite de la topologie.
Les variables historiques (NERON_SERVICE_HOST/PORT, NERON_CORE_URL,
NERON_LLM_URL) sont derivees du plan et posees dans l'environnement AVANT
l'import du module, pour ne rien casser cote enregistrement au registry.
"""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import uvicorn
import yaml

NERON_ROOT = Path(os.getenv("NERON_ROOT", "/etc/neronOS"))
SERVER_PLAN = NERON_ROOT / "neron.server.yaml"


def _load_nodes() -> dict:
    data = yaml.safe_load(SERVER_PLAN.read_text(encoding="utf-8")) or {}
    nodes = data.get("nodes")
    if not isinstance(nodes, dict):
        raise SystemExit(f"serve: section 'nodes' absente de {SERVER_PLAN}")
    return nodes


def _node(nodes: dict, name: str) -> dict:
    cfg = nodes.get(name)
    if not isinstance(cfg, dict):
        raise SystemExit(f"serve: noeud '{name}' absent ou malforme dans {SERVER_PLAN}")
    return cfg


def _port(name: str, cfg: dict) -> int:
    if "port" in cfg:
        return int(cfg["port"])
    found = sorted((int(v), k) for k, v in cfg.items()
                   if k.endswith("_port") and isinstance(v, int))
    if not found:
        raise SystemExit(f"serve: aucun port pour '{name}' dans {SERVER_PLAN}")
    port, key = found[0]
    if len(found) > 1:
        print(f"serve: '{name}' declare {len(found)} ports, '{key}' retenu ({port})",
              flush=True)
    return port


def main(argv: list[str]) -> None:
    if len(argv) != 1:
        raise SystemExit("usage: python -m common.serve <nom-du-noeud>")
    name = argv[0]
    nodes = _load_nodes()
    cfg = _node(nodes, name)

    host = str(cfg.get("host") or "").strip()
    if not host:
        raise SystemExit(f"serve: pas d'hote pour '{name}' dans {SERVER_PLAN}")
    bind = str(cfg.get("bind") or host).strip()
    port = _port(name, cfg)

    os.environ.setdefault("NERON_SERVICE_HOST", host)
    os.environ.setdefault("NERON_SERVICE_PORT", str(port))
    if "core" in nodes:
        c = _node(nodes, "core")
        os.environ.setdefault("NERON_CORE_URL", f"http://{c['host']}:{_port('core', c)}")
    if "llm" in nodes:
        l = _node(nodes, "llm")
        os.environ.setdefault("NERON_LLM_URL", f"http://{l['host']}:{_port('llm', l)}/llm")

    module = importlib.import_module(f"{name}.app")
    app = getattr(module, "app", None)
    if app is None:
        raise SystemExit(f"serve: {name}.app n'expose pas d'objet 'app'")

    print(f"serve: {name} -> {bind}:{port} (annonce {host})", flush=True)
    uvicorn.run(app, host=bind, port=port,
                log_level=os.getenv("NERON_LOG_LEVEL", "info"))


if __name__ == "__main__":
    main(sys.argv[1:])
