# agent.py
import os
import shutil
import argparse
from pathlib import Path

from planner import plan
from coder import code
from file_manager import list_files, read_file, write_file, set_workspace

# ── Chemins ───────────────────────────────────────────────────────────────────

SOURCE_PATH = "/etc/neron/server/core/"
WORKSPACE = str(Path.home() / "neron_workspace")

# ── Verbose global ────────────────────────────────────────────────────────────

_VERBOSE = False


def vlog(*args, **kwargs) -> None:
    """Print uniquement si --verbose est actif."""
    if _VERBOSE:
        print(*args, **kwargs)


# ── Sécurité ──────────────────────────────────────────────────────────────────

def _init_workspace() -> None:
    os.makedirs(WORKSPACE, exist_ok=True)

    dest = os.path.join(WORKSPACE, "core")
    if not os.path.exists(dest):
        if os.path.isdir(SOURCE_PATH):
            shutil.copytree(SOURCE_PATH, dest)
            print(f"  📁 Sources copiées : {SOURCE_PATH} → {dest}")
        else:
            os.makedirs(dest, exist_ok=True)
            print(f"  ⚠️  Source '{SOURCE_PATH}' introuvable — workspace vide créé.")

    set_workspace(WORKSPACE)
    print(f"  🔒 Workspace verrouillé : {WORKSPACE}")


# ── Logique principale ────────────────────────────────────────────────────────

def run(task: str, dry_run: bool = False, verbose: bool = False) -> None:
    global _VERBOSE
    _VERBOSE = verbose

    print("\n🚀 Démarrage de l'agent")
    print(f"   Mode    : {'DRY-RUN (aucune écriture)' if dry_run else 'ÉCRITURE dans workspace'}")
    print(f"   Verbose : {'activé' if verbose else 'désactivé'}")
    print(f"   Tâche   : {task}\n")

    _init_workspace()

    workspace_core = os.path.join(WORKSPACE, "core")

    # ── Étape 1 : analyse ────────────────────────────────────────────────────
    print("🔍 Analyse des fichiers...")
    files = list_files(workspace_core)

    if not files:
        print("  ⚠️  Aucun fichier source trouvé dans le workspace.")
        return

    print(f"  {len(files)} fichier(s) trouvé(s) :")
    for f in files:
        print(f"    - {f}")

    context = "\n".join(files)

    # ── Étape 2 : planification ──────────────────────────────────────────────
    print("\n🧠 Planification en cours...")
    vlog("  [verbose] Contexte envoyé au planner :")
    vlog(f"  {context}\n")

    try:
        action_plan = plan(task, context)
    except (ValueError, RuntimeError) as e:
        print(f"  ❌ Échec de la planification : {e}")
        return

    print("\n── Plan généré ──────────────────────────────────────────────────")
    print(action_plan)
    print("─────────────────────────────────────────────────────────────────\n")

    # ── Étape 3 : génération et écriture ─────────────────────────────────────
    print("💻 Génération du code...")
    errors = []

    for file_path in files:
        print(f"\n  📄 Traitement : {os.path.relpath(file_path, WORKSPACE)}")

        try:
            content = read_file(file_path)

            vlog(f"  [verbose] Contenu original ({len(content)} chars) :")
            vlog("  " + "\n  ".join(content.splitlines()[:20]))
            if len(content.splitlines()) > 20:
                vlog("  ...")

            new_code = code(action_plan, content)

            vlog(f"\n  [verbose] Code généré ({len(new_code)} chars) :")
            vlog("  " + "\n  ".join(new_code.splitlines()[:20]))
            if len(new_code.splitlines()) > 20:
                vlog("  ...")

            if dry_run:
                print("  [DRY-RUN] Code généré (non écrit) :")
                print("  " + "\n  ".join(new_code.splitlines()[:10]) + "\n  ...")
            else:
                write_file(file_path, new_code)
                print("  ✅ Fichier mis à jour dans le workspace.")

        except PermissionError as e:
            msg = f"🚫 Accès refusé sur '{file_path}' : {e}"
            print(f"  {msg}")
            errors.append(msg)
        except (ValueError, RuntimeError) as e:
            msg = f"⚠️  Ignoré '{file_path}' : {e}"
            print(f"  {msg}")
            errors.append(msg)

    # ── Rapport final ─────────────────────────────────────────────────────────
    print("\n── Rapport ──────────────────────────────────────────────────────")
    if errors:
        print(f"  {len(errors)} erreur(s) rencontrée(s) :")
        for err in errors:
            print(f"    • {err}")
    else:
        print("  ✅ Toutes les opérations ont réussi.")

    if not dry_run:
        print(f"\n  📂 Résultats disponibles dans : {WORKSPACE}")
        print("  ⚠️  Vérifiez le code avant tout déploiement vers /server.")
    print("─────────────────────────────────────────────────────────────────\n")


# ── Entrée CLI ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Agent de refactorisation Néron — sandbox workspace uniquement."
    )
    parser.add_argument(
        "task",
        nargs="?",
        default="Refactoriser le projet pour améliorer structure et lisibilité",
        help="Tâche à effectuer (entre guillemets).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Génère le code sans écrire aucun fichier.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Affiche les prompts, le contenu original et les réponses complètes du LLM.",
    )
    args = parser.parse_args()
    run(args.task, dry_run=args.dry_run, verbose=args.verbose)
