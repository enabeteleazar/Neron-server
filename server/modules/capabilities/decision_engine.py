from __future__ import annotations

from modules.capabilities.models import CapabilityMatch, IntentUnderstanding
from modules.capabilities.router import normalize_text


class DecisionEngine:
    _OPERATIONAL_DOMAINS = {"logs", "backups", "sqlite", "systemd"}

    def decide(
        self,
        text: str,
        understanding: IntentUnderstanding,
        match: CapabilityMatch | None,
    ) -> tuple[str, float, str]:
        intent = understanding.intent
        domain = understanding.domain

        if intent.requested_type:
            decision = f"create_{intent.requested_type}"
            return decision, intent.confidence, "Création demandée explicitement."

        if match is not None:
            if match.missing_tools:
                return (
                    "create_tool",
                    match.score,
                    "La capacité existe mais un tool déclaré est indisponible.",
                )
            if match.capability.capability_type == "agent":
                return "execute_agent", match.score, "Agent pertinent trouvé."
            return "execute_tool", match.score, "Tool pertinent trouvé."

        if intent.durable or intent.action in {"surveillance", "notification"}:
            return (
                "create_agent",
                max(intent.confidence, domain.confidence),
                "La demande implique une capacité durable.",
            )

        if (
            domain.domain in self._OPERATIONAL_DOMAINS
            and intent.action in {"analyse", "resume", "diagnostic", "recherche"}
            and not self._is_inline_payload_request(text)
        ):
            return (
                "create_agent",
                round(max(domain.confidence, intent.confidence), 3),
                "Aucun agent pertinent ne couvre ce domaine opérationnel.",
            )

        if domain.domain != "unknown":
            return (
                "create_tool",
                round(max(domain.confidence, intent.confidence), 3),
                "Le domaine est identifié mais aucune capacité ne le couvre.",
            )

        if intent.action in {
            "analyse",
            "resume",
            "diagnostic",
            "calcul",
            "recherche",
            "comparaison",
        }:
            return (
                "create_tool",
                round(max(domain.confidence, intent.confidence), 3),
                "La demande ponctuelle nécessite un nouveau tool.",
            )

        return (
            "fallback_conversation",
            understanding.confidence,
            "Aucune intention opérationnelle suffisamment précise.",
        )

    def _is_inline_payload_request(self, text: str) -> bool:
        query = normalize_text(text)
        return any(
            marker in query
            for marker in ("ces logs", "ce contenu", "ces donnees", "ce texte")
        ) or (
            "logs" in query
            and any(marker in query for marker in ("resume", "resumer"))
            and "automatiquement" not in query
        )
