from __future__ import annotations

from modules.capabilities.models import Intent
from modules.capabilities.router import normalize_text


class IntentExtractor:
    _ACTIONS: tuple[tuple[str, tuple[str, ...], float], ...] = (
        ("creation", ("cree", "creer", "genere", "ajoute"), 0.97),
        ("surveillance", ("surveille", "surveillance", "en continu", "suivi"), 0.96),
        ("notification", ("previens moi", "notifie", "alerte"), 0.95),
        ("comparaison", ("compare", "comparaison"), 0.94),
        ("diagnostic", ("diagnostic", "verifie", "controle"), 0.93),
        ("resume", ("resume", "resumer", "synthese"), 0.93),
        ("analyse", ("analyse", "analyser", "inspecte", "inspecter"), 0.93),
        ("calcul", ("calcule", "calcul", "combien", "convertis", "conversion"), 0.92),
        ("recherche", ("cherche", "recherche", "trouve", "liste", "lis "), 0.9),
    )
    _DURABLE = (
        "automatiquement",
        "regulierement",
        "chaque jour",
        "tous les jours",
        "periodiquement",
        "en continu",
        "surveille",
        "previens moi",
        "alerte",
        "suivi",
    )

    def extract(self, text: str) -> Intent:
        query = normalize_text(text)
        requested_type = None
        if "agent" in query and any(
            token in query for token in ("cree", "creer", "genere")
        ):
            requested_type = "agent"
        elif any(token in query for token in ("tool", "outil")) and any(
            token in query for token in ("cree", "creer", "genere")
        ):
            requested_type = "tool"

        durable = any(token in query for token in self._DURABLE)
        for action, terms, confidence in self._ACTIONS:
            if any(term in query for term in terms):
                return Intent(
                    action=action,
                    confidence=confidence,
                    durable=durable,
                    requested_type=requested_type,
                )
        return Intent(
            action="conversation",
            confidence=0.35 if query else 0.0,
            durable=False,
            requested_type=requested_type,
        )
