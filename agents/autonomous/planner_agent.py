from __future__ import annotations

from datetime import datetime

from modules.autonomous.scheduler import AutonomousScheduler
from core.modules.oblivia.semantic.semantic_search import ObsidianSemanticSearch


class AutonomousPlannerAgent:
    def __init__(self, vault_path: str):
        self.vault_path = vault_path

        self.semantic = ObsidianSemanticSearch(vault_path)

        self.scheduler = AutonomousScheduler()

    def create_plan(self, objective: str) -> dict:
        context = self.semantic.search(objective, limit=3)

        context_lines = []

        for item in context:
            context_lines.append(
                f"- {item['title']} ({item['path']})"
            )

        plan_steps = [
            "Analyser l’objectif et identifier le périmètre.",
            "Rechercher le contexte existant dans la mémoire Obsidian.",
            "Découper l’objectif en sous-tâches techniques.",
            "Identifier les fichiers, services ou modules concernés.",
            "Proposer une action contrôlée.",
            "Attendre validation humaine avant exécution.",
            "Après validation, exécuter l’action.",
            "Vérifier le résultat.",
            "Enregistrer le résultat dans la mémoire Obsidian.",
        ]

        task = self.scheduler.add_task(
            title=objective,
            objective=objective,
            status="pending",
            payload={
                "objective": objective,
                "created_by": "autonomous_planner",
                "context": context,
                "plan": plan_steps,
                "generated_at": datetime.utcnow().isoformat(),
            },
        )

        response = (
            f"Plan autonome créé pour : {objective}\n\n"
            f"Tâche autonome enregistrée : #{task['id']}\n\n"
            "Plan :\n"
        )

        for idx, step in enumerate(plan_steps, start=1):
            response += f"{idx}. {step}\n"

        if context_lines:
            response += "\nContexte mémoire utilisé :\n"
            response += "\n".join(context_lines)

        return {
            "response": response,
            "intent": "autonomous_plan",
            "agent": "autonomous_planner",
            "task": task,
            "metadata": {
                "objective": objective,
                "context_count": len(context),
                "generated_at": datetime.utcnow().isoformat(),
            },
        }
