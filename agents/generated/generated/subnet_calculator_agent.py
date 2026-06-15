from __future__ import annotations

import ipaddress
import re

AGENT_SPEC = {
    "capabilities": [
        "deterministic_response"
    ],
    "goal": "Créer un agent nommé subnet_calculator_agent qui calcule les informations d'un réseau IPv4 ou IPv6.",
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
AGENT_SPEC_SIGNATURE = 'capabilities deterministic response goal creer un agent nomme subnet calculator agent qui calcule les informations d un reseau ipv4 ou ipv6 inputs text kind agent name subnet calculator agent outputs response safety filesystem limited network none required title agent subnet calculator agent'


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
                "Fournissez un réseau IPv4 ou IPv6 au format CIDR, par exemple "
                "192.168.1.10/24 ou 2001:db8::/64."
            )

        first_address = network.network_address
        last_address = network.broadcast_address
        ip_type = f"IPv{network.version}"

        lines = [
            f"Réseau: {network.network_address}/{network.prefixlen}",
            f"Type IPv4/IPv6: {ip_type}",
            f"Préfixe: /{network.prefixlen}",
            f"Première adresse: {first_address}",
            f"Dernière adresse: {last_address}",
            f"Nombre total d'adresses: {network.num_addresses}",
        ]

        if isinstance(network, ipaddress.IPv4Network):
            usable_hosts = max(network.num_addresses - 2, 0)
            first_host = network.network_address + 1 if usable_hosts else "n/a"
            last_host = network.broadcast_address - 1 if usable_hosts else "n/a"
            lines.extend(
                [
                    f"Adresse réseau: {network.network_address}",
                    f"Masque: {network.netmask}",
                    f"Wildcard: {network.hostmask}",
                    f"Broadcast: {network.broadcast_address}",
                    f"Première adresse utilisable: {first_host}",
                    f"Dernière adresse utilisable: {last_host}",
                    f"Nombre d'hôtes utilisables: {usable_hosts}",
                ]
            )

        return "\n".join(lines)

    def _extract_network(
        self, text: str
    ) -> ipaddress.IPv4Network | ipaddress.IPv6Network | None:
        for candidate in re.findall(r"(?<!\S)\S+/\d{1,3}(?!\S)", text):
            try:
                network = ipaddress.ip_network(candidate, strict=False)
            except ValueError:
                continue

            if isinstance(
                network, (ipaddress.IPv4Network, ipaddress.IPv6Network)
            ):
                return network
        return None
