from __future__ import annotations

import subprocess

from agents.builtin.base_agent import get_logger
from server.common.runtime.governor import get_runtime_governor
from core.status import get_status, get_health_score

logger = get_logger("system_agent")


class SystemAgent:
    async def run(self, query: str) -> str:

        q = query.lower()

        try:
            if any(w in q for w in ["service", "services", "systemd", "actifs", "running"]):
                return self._run_services()

            if any(w in q for w in ["port", "ports", "reseau", "réseau", "connexion", "connexions", "ss -tulpn", "netstat"]):
                return self._run_ports()

            if any(w in q for w in ["cpu", "ram", "memoire", "mémoire", "ressource", "ressources", "process"]):
                return self._format_resources(get_status())

            if any(w in q for w in ["anomalie", "anomalies", "probleme", "problème", "erreur", "crash"]):
                return "Analyse des anomalies désactivée (module Watchdog retiré)."

            return self._format_health(get_status(), get_health_score())

        except Exception as e:
            logger.error("SystemAgent error: %s", e)
            return f"Impossible de récupérer l'état du système : {e}"

    def _safe_cmd(self, cmd: list[str], timeout: int = 10) -> str:
        governor = get_runtime_governor()

        if not governor.authorize_system_command(
            actor="system_agent",
            command=cmd,
            reason="system diagnostic read",
        ):
            return "Commande système bloquée par RuntimeGovernor."

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

        output = result.stdout.strip() or result.stderr.strip()

        if not output:
            return "Aucune donnée retournée."

        return output[:12000]

    def _run_services(self) -> str:
        output = self._safe_cmd([
            "systemctl",
            "list-units",
            "--type=service",
            "--state=running",
            "--no-pager",
            "--plain",
        ])

        lines = output.splitlines()
        filtered = []

        for line in lines:
            if not line.strip():
                continue
            if line.startswith("UNIT "):
                continue
            if "loaded active running" in line:
                filtered.append(line)

        if not filtered:
            return "Aucun service actif détecté."

        important = []
        others = []

        for line in filtered:
            if "neron" in line.lower() or "ollama" in line.lower() or "ssh" in line.lower():
                important.append(line)
            else:
                others.append(line)

        response = [f"Services actifs détectés : {len(filtered)}"]

        if important:
            response.append("")
            response.append("Services importants :")
            response.extend(f"- {line}" for line in important[:20])

        if others:
            response.append("")
            response.append("Autres services :")
            response.extend(f"- {line}" for line in others[:40])

        if len(others) > 40:
            response.append(f"... {len(others) - 40} autres services masqués.")

        return "\n".join(response)

    def _run_ports(self) -> str:
        output = self._safe_cmd(["ss", "-tulpn"])

        if not output:
            return "Aucun port ouvert détecté."

        known_ports = {
            "22": "SSH",
            "8010": "Néron Core",
            "8020": "Néron Doctor",
            "8030": "Néron Monitor",
            "8081": "Néron Vocal",
            "8123": "Home Assistant",
            "8443": "HTTPS",
            "8765": "Néron LLM",
            "11434": "Ollama",
            "18789": "Néron Gateway",
            "27960": "LLaMA.cpp",
        }

        ignored_ports = {"53", "631"}

        lines = output.splitlines()
        detected = {}

        for line in lines:
            if "LISTEN" not in line:
                continue

            parts = line.split()
            if len(parts) < 5:
                continue

            addr = parts[4]
            if ":" not in addr:
                continue

            port = addr.rsplit(":", 1)[-1]

            if port in ignored_ports:
                continue

            if port in known_ports:
                detected[port] = known_ports[port]

        response = ["Ports applicatifs détectés :"]

        if not detected:
            response.append("Aucun port applicatif connu détecté.")
        else:
            for port in sorted(detected, key=lambda p: int(p)):
                response.append(f"• {port:<5} → {detected[port]}")

        response.append("")
        response.append("Commande utilisée : ss -tulpn")

        return "\n".join(response)

    def _format_resources(self, sys_: dict) -> str:
        return (
            f"CPU : {sys_.get('cpu_pct')}% | "
            f"RAM : {sys_.get('ram_pct')}% ({sys_.get('ram_used_mb')} MB) | "
            f"Disque : {sys_.get('disk_pct')}% | "
            f"Process Néron : {sys_.get('process_ram_mb')} MB"
        )

    def _format_health(self, sys_: dict, score: dict) -> str:
        return (
            f"{score['level']} — Score santé : {score['score']}/100\n"
            f"CPU : {sys_.get('cpu_pct')}% | RAM : {sys_.get('ram_pct')}% | "
            f"Disque : {sys_.get('disk_pct')}%"
        )

    def _format_anomalies(self, anomalies: list) -> str:
        if not anomalies:
            return "✅ Aucune anomalie détectée sur les 7 derniers jours."

        lines = [f"🔍 {len(anomalies)} anomalie(s) détectée(s) :"]
        for a in anomalies[:5]:
            lines.append(f"  • {a.get('message', '?')}")
        return "\n".join(lines)
