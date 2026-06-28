from __future__ import annotations

from typing import Any


class ReasoningAgent:

    def decide(
        self,
        objective: str,
    ) -> dict[str, Any]:

        objective_lower = objective.lower()

        # ─────────────────────────────
        # SYSTEM
        # ─────────────────────────────

        if (
            "disque" in objective_lower
            or "espace disque" in objective_lower
            or "stockage" in objective_lower
        ):
            return {
                "success": True,
                "action": "system.disk_usage",
                "risk": "low",
                "requires_validation": False,
                "reasoning": (
                    "Objectif lié au stockage système."
                ),
            }

        if (
            "restart" in objective_lower
            or "redémarre" in objective_lower
            or "redemarre" in objective_lower
        ):
            return {
                "success": True,
                "action": "system.restart_service",
                "risk": "medium",
                "requires_validation": True,
                "reasoning": (
                    "Redémarrage service détecté."
                ),
            }

        # ─────────────────────────────
        # MEMORY
        # ─────────────────────────────

        if (
            "mémoire" in objective_lower
            or "memoire" in objective_lower
            or "obsidian" in objective_lower
        ):
            return {
                "success": True,
                "action": "memory.semantic_search",
                "risk": "low",
                "requires_validation": False,
                "reasoning": (
                    "Recherche mémoire détectée."
                ),
            }

        # ─────────────────────────────
        # GIT
        # ─────────────────────────────

        if (
            "git pull" in objective_lower
            or "mettre à jour" in objective_lower
            or "mise à jour" in objective_lower
        ):
            return {
                "success": True,
                "action": "system.git_pull",
                "risk": "medium",
                "requires_validation": True,
                "reasoning": (
                    "Action git détectée."
                ),
            }

        # ─────────────────────────────
        # UNKNOWN
        # ─────────────────────────────

        return {
            "success": False,
            "action": None,
            "risk": "unknown",
            "requires_validation": True,
            "reasoning": (
                "Aucune stratégie trouvée."
            ),
        }
