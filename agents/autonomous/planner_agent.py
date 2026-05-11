from datetime import datetime

from agents.autonomous.task_state import AutonomousTask, TaskStore
from agents.memory.obsidian_agent import ObsidianAgent


class AutonomousPlannerAgent:
    def __init__(self, vault_path: str = "/etc/neron/obsidian-vault"):
        self.vault_path = vault_path
        self.memory = ObsidianAgent(vault_path)
        self.store = TaskStore()

    def create_plan(self, objective: str) -> dict:
        objective = objective.strip()

        if not objective:
            return {
                "success": False,
                "response": "Objectif vide.",
                "error": "empty_objective",
            }

        plan = self._basic_plan(objective)
        now = datetime.now().isoformat(timespec="seconds")

        task = AutonomousTask(
            objective=objective,
            plan=plan,
            status="waiting_validation",
            created_at=now,
            updated_at=now,
            verification="Validation humaine requise avant exécution.",
        )

        stored = self.store.add(task)

        note_content = self._format_task_note(stored)
        memory_result = self.memory.handle(
            f"Enregistre ceci {note_content}"
        )

        stored["memory_result"] = memory_result

        return {
            "success": True,
            "response": self._format_response(stored),
            "intent": "autonomous_plan",
            "agent": "autonomous_planner_agent",
            "task": stored,
        }

    def _basic_plan(self, objective: str) -> list[str]:
        return [
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

    def _format_task_note(self, task: dict) -> str:
        plan_md = "\n".join(f"- [ ] {step}" for step in task["plan"])

        return f"""Tâche autonome proposée : {task["objective"]}

## Objectif
{task["objective"]}

## Statut
{task["status"]}

## Plan
{plan_md}

## Vérification
{task["verification"]}

## Sécurité
Aucune action système ne doit être exécutée sans validation humaine.

Tags: #neron #agent #autonome #planner
"""

    def _format_response(self, task: dict) -> str:
        plan = "\n".join(f"{i+1}. {step}" for i, step in enumerate(task["plan"]))

        return (
            f"Plan autonome créé pour : {task['objective']}\n\n"
            f"{plan}\n\n"
            "Statut : attente de validation humaine."
        )
