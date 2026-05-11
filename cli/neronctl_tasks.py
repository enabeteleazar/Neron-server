from __future__ import annotations

import argparse

from core.modules.autonomous.scheduler import AutonomousScheduler
from core.autonomous.execution_logger import ExecutionLogger


def print_task(task: dict) -> None:
    print(f"#{task['id']} [{task['status']}] priority={task['priority']}")
    print(f"Title     : {task['title']}")
    print(f"Objective : {task['objective']}")
    print(f"Created   : {task['created_at']}")
    print(f"Updated   : {task['updated_at']}")
    print(f"Last run  : {task.get('last_run_at')}")
    print(f"Payload   : {task.get('payload')}")


def cmd_list(args) -> None:
    scheduler = AutonomousScheduler()
    tasks = scheduler.list_tasks(status=args.status, limit=args.limit)

    if not tasks:
        print("Aucune tâche trouvée.")
        return

    for task in tasks:
        print(
            f"#{task['id']:<4} "
            f"{task['status']:<18} "
            f"prio={task['priority']} "
            f"{task['title']}"
        )


def cmd_show(args) -> None:
    task = AutonomousScheduler().get_task(args.id)

    if not task:
        print(f"Tâche #{args.id} introuvable.")
        return

    print_task(task)


def cmd_logs(args) -> None:
    logs = ExecutionLogger().list_logs(task_id=args.id, limit=args.limit)

    if not logs:
        print(f"Aucun log pour la tâche #{args.id}.")
        return

    for log in logs:
        print(
            f"[{log['created_at']}] "
            f"{log['level']:<5} "
            f"TASK #{log['task_id']} - {log['message']}"
        )


def cmd_add(args) -> None:
    task = AutonomousScheduler().add_task(
        title=args.title,
        objective=args.objective,
        status=args.status,
        priority=args.priority,
    )

    print("Tâche créée :")
    print_task(task)


def cmd_done(args) -> None:
    task = AutonomousScheduler().mark_done(args.id)

    if not task:
        print(f"Tâche #{args.id} introuvable.")
        return

    print("Tâche marquée comme done :")
    print_task(task)


def cmd_cancel(args) -> None:
    task = AutonomousScheduler().set_status(args.id, "cancelled")

    if not task:
        print(f"Tâche #{args.id} introuvable.")
        return

    print("Tâche annulée :")
    print_task(task)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="neron task",
        description="Gestion des tâches autonomes Néron",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("list", help="Lister les tâches")
    p.add_argument("--status", default=None)
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("show", help="Afficher une tâche")
    p.add_argument("id", type=int)
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("logs", help="Afficher les logs d'une tâche")
    p.add_argument("id", type=int)
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=cmd_logs)

    p = sub.add_parser("add", help="Créer une tâche")
    p.add_argument("title")
    p.add_argument("objective")
    p.add_argument("--status", default="pending")
    p.add_argument("--priority", type=int, default=5)
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("done", help="Marquer une tâche done")
    p.add_argument("id", type=int)
    p.set_defaults(func=cmd_done)

    p = sub.add_parser("cancel", help="Annuler une tâche")
    p.add_argument("id", type=int)
    p.set_defaults(func=cmd_cancel)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
