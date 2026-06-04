from __future__ import annotations

import ipaddress
import re

AGENT_SPEC = {
    "capabilities": [
        "deterministic_response"
    ],
    "goal": "Créer un agent nommé subnet_calculator_agent qui calcule les informations d'un réseau IPv4.",
    "inputs": [
        "text"
    ],
    "kind": "agent",
    "name": "subnet_calculator_agent",
    "outputs": [
        "response"
    ],
    "safety": {
        "filesystem": "limited",
        "network": "none_required"
    },
    "title": "Agent subnet_calculator_agent"
}
AGENT_SPEC_SIGNATURE = 'capabilities deterministic response goal creer un agent nomme subnet calculator agent qui calcule les informations d un reseau ipv4 inputs text kind agent name subnet calculator agent outputs response safety filesystem limited network none required title agent subnet calculator agent'


class Agent:
    name = 'subnet_calculator_agent'

    async def execute(self, text: str = "") -> dict:
        query = text or ""
        response = self._calculate(query)
        return {
            "status": "ok",
            "agent": self.name,
            "response": response,
        }

    def _calculate(self, text: str) -> str:
        network = self._extract_network(text)
        if network is None:
            return (
                "Fournissez un réseau IPv4 au format CIDR, par exemple "
                "192.168.1.10/24."
            )

        hosts = list(network.hosts())
        first_host = str(hosts[0]) if hosts else "n/a"
        last_host = str(hosts[-1]) if hosts else "n/a"

        return "\n".join(
            [
                f"Réseau: {network.network_address}/{network.prefixlen}",
                f"Adresse réseau: {network.network_address}",
                f"Masque: {network.netmask}",
                f"Wildcard: {network.hostmask}",
                f"Broadcast: {network.broadcast_address}",
                f"Première adresse utilisable: {first_host}",
                f"Dernière adresse utilisable: {last_host}",
                f"Nombre total d'adresses: {network.num_addresses}",
                f"Nombre d'hôtes utilisables: {len(hosts)}",
            ]
        )

    def _extract_network(self, text: str) -> ipaddress.IPv4Network | None:
        match = re.search(
            r"\b(?:\d{1,3}\.){3}\d{1,3}/(?:\d|[12]\d|3[0-2])\b",
            text,
        )
        if not match:
            return None

        try:
            network = ipaddress.ip_network(match.group(0), strict=False)
        except ValueError:
            return None

        if isinstance(network, ipaddress.IPv4Network):
            return network
        return None
