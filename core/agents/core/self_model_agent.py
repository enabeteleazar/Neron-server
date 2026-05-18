from __future__ import annotations

from core.self_model.self_model import load_self_model_state


class SelfModelAgent:
    name = "self_model"

    async def handle(self, query: str) -> str:
        data = load_self_model_state()

        runtime = data.get("runtime", {})
        services = data.get("services", {})
        cognitive = data.get("cognitive_state", {})

        lines = []

        lines.append("État interne de Néron :")

        lines.append(
            f"- Santé globale : {data.get('health_global')}"
        )

        lines.append(
            f"- Santé temps réel : {data.get('health_realtime')}"
        )

        lines.append(
            f"- Santé historique : {data.get('health_historical')}"
        )

        lines.append(
            f"- CPU : {runtime.get('cpu_usage')}%"
        )

        lines.append(
            f"- RAM : {runtime.get('ram_usage')}%"
        )

        lines.append(
            f"- Disque : {runtime.get('disk_usage')}%"
        )

        lines.append(
            f"- Dernier objectif : {data.get('active_goal')}"
        )

        lines.append(
            f"- Boucle cognitive : {'active' if cognitive.get('autonomous_loop') else 'inactive'}"
        )

        lines.append(
            f"- Self-Model : {'actif' if cognitive.get('self_model_loop') else 'inactif'}"
        )

        active_services = [
            name
            for name, status in services.items()
            if status == "active"
        ]

        lines.append(
            "- Services actifs : "
            + ", ".join(active_services)
        )

        diagnostics = data.get("diagnostics", [])

        if diagnostics:
            lines.append("- Diagnostics :")

            for diagnostic in diagnostics:
                lines.append(f"  • {diagnostic}")

        recommendations = data.get(
            "recommendations",
            [],
        )

        if recommendations:
            lines.append("- Recommandations :")

            for recommendation in recommendations:
                lines.append(f"  • {recommendation}")

        return "\n".join(lines)
