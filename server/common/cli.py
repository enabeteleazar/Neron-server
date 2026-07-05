from __future__ import annotations

import argparse
import os
import sys
from typing import Any

import httpx

from common.paths import NERON_SECRETS_FILE

def _api_key() -> str:
    configured = os.getenv("NERON_API_KEY", "")
    if configured:
        return configured
    try:
        for line in NERON_SECRETS_FILE.open(encoding="utf-8"):
            name, separator, value = line.strip().partition("=")
            if separator and name.strip() == "NERON_API_KEY":
                return value.strip().strip("\"'")
    except OSError:
        pass
    return ""


def _request(path: str) -> dict[str, Any]:
    core_url = os.getenv("NERON_CORE_URL", "http://localhost:8010").rstrip("/")
    api_key = _api_key()
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        response = httpx.get(
            f"{core_url}{path}",
            headers=headers,
            timeout=5.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Core API unavailable: {exc}") from exc
    return response.json()


def _endpoint(service_name: str | None = None) -> str:
    if service_name is None:
        return "/registry/topology"
    return f"/registry/topology/{service_name}"


def registry_output(topology: dict[str, Any], *, compact: bool = False) -> str:
    lines = []
    if not compact:
        lines.extend(
            [
                "Néron Registry",
                "",
                f"Status : {topology['status']}",
                "",
                f"Services : {topology['service_count']}",
                "",
            ]
        )
    for service in topology["services"]:
        endpoint = f"{service['host']}:{service['port']}"
        lines.append(
            f"{service['name']:<14} {service['status']:<10} {endpoint}"
        )
    return "\n".join(lines)


def service_output(service: dict[str, Any]) -> str:
    capabilities = ", ".join(service["capabilities"]) or "—"
    return "\n".join(
        [
            f"Nom            : {service['name']}",
            f"Status         : {service['status']}",
            f"Host           : {service['host']}",
            f"Port           : {service['port']}",
            f"Capabilities   : {capabilities}",
            f"Registered at  : {service['registered_at']}",
            f"Last heartbeat : {service['last_seen']}",
            f"Age            : {service['age_seconds']}s",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="neron")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("registry")
    subparsers.add_parser("services")
    service_parser = subparsers.add_parser("service")
    service_parser.add_argument("service_name")
    args = parser.parse_args(argv)

    try:
        if args.command == "service":
            print(service_output(_request(_endpoint(args.service_name))))
        else:
            print(
                registry_output(
                    _request(_endpoint()),
                    compact=args.command == "services",
                )
            )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
