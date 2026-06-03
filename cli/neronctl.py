#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path("/etc/neron")
sys.path.insert(0, str(REPO))

from core.service_core.service_manager import ServiceManager, SERVICES
from core.modules.autonomous.scheduler import AutonomousScheduler
from core.autonomous.execution_logger import ExecutionLogger

manager = ServiceManager()


def print_task(task: dict) -> None:
    print(f"#{task['id']} [{task['status']}] priority={task['priority']}")
    print(f"Title     : {task['title']}")
    print(f"Objective : {task['objective']}")
    print(f"Created   : {task['created_at']}")
    print(f"Updated   : {task['updated_at']}")
    print(f"Last run  : {task.get('last_run_at')}")
    print(f"Payload   : {task.get('payload')}")


def cmd_task_list(args) -> None:
    tasks = AutonomousScheduler().list_tasks()[:args.limit]
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


def cmd_task_show(args) -> None:
    task = AutonomousScheduler().get_task(args.id)
    if not task:
        print(f"Tâche #{args.id} introuvable.")
        return
    print_task(task)


def cmd_task_logs(args) -> None:
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


def cmd_task_add(args) -> None:
    task = AutonomousScheduler().add_task(
        title=args.title,
        objective=args.objective,
        status=args.status,
        priority=args.priority,
    )
    print("Tâche créée :")
    print_task(task)


def cmd_task_done(args) -> None:
    print("Commande indisponible : AutonomousScheduler ne fournit pas encore mark_done().")


def cmd_task_cancel(args) -> None:
    print("Commande indisponible : AutonomousScheduler ne fournit pas encore set_status().")


def main() -> int:
    parser = argparse.ArgumentParser(prog="neronctl")
    sub = parser.add_subparsers(dest="module", required=True)

    svc = sub.add_parser("service", help="Gestion des services Néron")
    svc_sub = svc.add_subparsers(dest="action", required=True)

    svc_sub.add_parser("status-all")
    svc_sub.add_parser("start-all")
    svc_sub.add_parser("stop-all")
    svc_sub.add_parser("restart-all")

    for action in ["status", "start", "stop", "restart", "logs"]:
        p = svc_sub.add_parser(action)
        p.add_argument("service", choices=SERVICES.keys())

    task = sub.add_parser("task", help="Gestion des tâches autonomes")
    task_sub = task.add_subparsers(dest="action", required=True)

    p = task_sub.add_parser("list")
    p.add_argument("--status", default=None)
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_task_list)

    p = task_sub.add_parser("show")
    p.add_argument("id", type=int)
    p.set_defaults(func=cmd_task_show)

    p = task_sub.add_parser("logs")
    p.add_argument("id", type=int)
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=cmd_task_logs)

    p = task_sub.add_parser("add")
    p.add_argument("title")
    p.add_argument("objective")
    p.add_argument("--status", default="pending")
    p.add_argument("--priority", type=int, default=5)
    p.set_defaults(func=cmd_task_add)

    p = task_sub.add_parser("done")
    p.add_argument("id", type=int)
    p.set_defaults(func=cmd_task_done)

    p = task_sub.add_parser("cancel")
    p.add_argument("id", type=int)
    p.set_defaults(func=cmd_task_cancel)

    args = parser.parse_args()

    if args.module == "service":
        if args.action == "status-all":
            print(manager.status_all())
        elif args.action == "start-all":
            print(manager.start_all())
        elif args.action == "stop-all":
            print(manager.stop_all())
        elif args.action == "restart-all":
            print(manager.restart_all())
        elif args.action == "status":
            print(manager.status(args.service))
        elif args.action == "start":
            print(manager.start(args.service))
        elif args.action == "stop":
            print(manager.stop(args.service))
        elif args.action == "restart":
            print(manager.restart(args.service))
        elif args.action == "logs":
            print(manager.logs(args.service))
        return 0

    if args.module == "task":
        args.func(args)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
