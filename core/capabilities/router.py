from __future__ import annotations

import unicodedata

from core.capabilities.models import CapabilityDecision


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    normalized = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    return " ".join(
        "".join(char if char.isalnum() or char in "./:" else " " for char in normalized).split()
    )


class CapabilityRouter:
    _DANGEROUS = (
        "supprime",
        "efface",
        "formate le disque",
        "formatage du disque",
        "rm -rf",
        "mot de passe",
        "secret",
        "desactive la securite",
        "contourne",
        "attaque",
        "exfiltre",
    )
    _DURABLE = (
        "analyse automatiquement",
        "analyser automatiquement",
        "surveille",
        "surveillance",
        "previens moi",
        "resume regulierement",
        "resumer regulierement",
        "alerte",
        "chaque jour",
        "tous les jours",
        "periodiquement",
        "en continu",
        "suivi",
        "suis ",
        "maintien",
    )
    _PUNCTUAL_ACTIONS = (
        "analyse ",
        "analyser ",
        "resume ",
        "resumer ",
        "extrais ",
        "extraire ",
        "compare ",
        "comparer ",
        "verifie ",
        "verifier ",
        "lis ",
        "lire ",
    )
    _TOOL = (
        "date",
        "delai",
        "combien de jours",
        "calcule",
        "calcul",
        "conversion",
        "convertis",
        "subnet",
        "sous reseau",
        "diagnostic",
        "paques",
        "noel",
    )
    _DIRECT = (
        "bonjour",
        "salut",
        "hello",
        "merci",
    )

    def classify(self, text: str) -> CapabilityDecision | None:
        query = normalize_text(text)
        if not query:
            return None

        if any(token in query for token in self._DANGEROUS):
            return CapabilityDecision(
                decision="ask_human_validation",
                confidence=0.95,
                reason="La demande peut modifier ou exposer des ressources sensibles.",
                human_validation_required=True,
                safety_level="high",
            )

        explicit_agent = any(
            token in query
            for token in ("cree un agent", "creer un agent", "nouvel agent", "genere un agent")
        )
        explicit_tool = any(
            token in query
            for token in ("cree un tool", "creer un tool", "cree un outil", "creer un outil")
        )
        if explicit_agent:
            return self._creation("agent", "Création d'agent demandée explicitement.", 0.99)
        if explicit_tool:
            return self._creation("tool", "Création de tool demandée explicitement.", 0.99)

        if any(token in query for token in self._DURABLE):
            return CapabilityDecision(
                decision="create_agent",
                confidence=0.91,
                reason="La demande implique un suivi durable, un état ou des alertes.",
                capability_type="agent",
                requires_creation=True,
                creation_type="agent",
                async_required=True,
                safety_level="medium",
            )

        if any(token in query for token in self._TOOL):
            return CapabilityDecision(
                decision="create_tool",
                confidence=0.87,
                reason="La demande est courte, ponctuelle et déterministe.",
                capability_type="tool",
                requires_creation=True,
                creation_type="tool",
                async_required=True,
                safety_level="low",
            )

        if query.startswith(self._PUNCTUAL_ACTIONS):
            return CapabilityDecision(
                decision="create_tool",
                confidence=0.82,
                reason="La demande décrit une action ponctuelle sans capacité existante.",
                capability_type="tool",
                requires_creation=True,
                creation_type="tool",
                async_required=True,
                safety_level="low",
            )

        if query in self._DIRECT:
            return CapabilityDecision(
                decision="direct_answer",
                confidence=0.98,
                reason="Réponse conversationnelle directe.",
                capability_type="direct",
                safety_level="low",
            )

        return None

    def _creation(self, creation_type: str, reason: str, confidence: float) -> CapabilityDecision:
        return CapabilityDecision(
            decision=f"create_{creation_type}",
            confidence=confidence,
            reason=reason,
            capability_type=creation_type,
            requires_creation=True,
            creation_type=creation_type,
            async_required=True,
            safety_level="medium" if creation_type == "agent" else "low",
        )
