from __future__ import annotations

import difflib
import re
import shutil
from pathlib import Path
from typing import Any

from core.autonomous.file_editor import (
    FileEditor,
)

from core.autonomous.watchdog_notifier import (
    WatchdogNotifier,
)


class SelfHealingAgent:

    def __init__(self):

        self.editor = FileEditor()

        self.watchdog = WatchdogNotifier()

    def analyze_traceback(
        self,
        traceback_text: str,
    ) -> dict[str, Any]:

        self.watchdog.warning(
            "SelfHealing",
            "Erreur détectée → analyse automatique",
        )

        traceback_text = traceback_text.strip()

        attribute_pattern = re.search(
            (
                r"AttributeError:\s*"
                r"'(?P<class_name>[^']+)'"
                r"\s*object has no attribute\s*"
                r"'(?P<attribute>[^']+)'"
            ),
            traceback_text,
            re.MULTILINE | re.DOTALL,
        )

        if attribute_pattern:

            class_name = (
                attribute_pattern.group(
                    "class_name"
                )
            )

            missing_attribute = (
                attribute_pattern.group(
                    "attribute"
                )
            )

            self.watchdog.info(
                "SelfHealing",
                (
                    "AttributeError détecté : "
                    f"{class_name}.{missing_attribute}"
                ),
            )

            return {
                "success": True,
                "type": "attribute_error",
                "class_name": class_name,
                "missing_attribute": (
                    missing_attribute
                ),
                "risk": "low",
                "message": (
                    "Méthode ou attribut "
                    f"manquant détecté : "
                    f"{class_name}."
                    f"{missing_attribute}"
                ),
                "can_auto_fix": True,
                "suggestion": (
                    "Ajouter une méthode stub "
                    f"'{missing_attribute}' "
                    f"dans la classe "
                    f"{class_name}."
                ),
            }

        syntax_pattern = re.search(
            r"SyntaxError:",
            traceback_text,
        )

        if syntax_pattern:

            self.watchdog.warning(
                "SelfHealing",
                "SyntaxError détectée",
            )

            return {
                "success": True,
                "type": "syntax_error",
                "risk": "medium",
                "message": (
                    "Erreur de syntaxe détectée."
                ),
                "can_auto_fix": False,
                "suggestion": (
                    "Rollback automatique conseillé."
                ),
            }

        import_pattern = re.search(
            (
                r"(ModuleNotFoundError|ImportError)"
            ),
            traceback_text,
        )

        if import_pattern:

            self.watchdog.warning(
                "SelfHealing",
                "Erreur import détectée",
            )

            return {
                "success": True,
                "type": "import_error",
                "risk": "medium",
                "message": (
                    "Erreur import détectée."
                ),
                "can_auto_fix": False,
                "suggestion": (
                    "Vérifier dépendances Python."
                ),
            }

        network_pattern = re.search(
            (
                r"(ConnectionError|ReadError|"
                r"TimeoutError|NetworkError)"
            ),
            traceback_text,
        )

        if network_pattern:

            self.watchdog.warning(
                "SelfHealing",
                "Erreur réseau détectée",
            )

            return {
                "success": True,
                "type": "network_error",
                "risk": "low",
                "message": (
                    "Erreur réseau détectée."
                ),
                "can_auto_fix": True,
                "suggestion": (
                    "Restart service ou retry."
                ),
            }

        self.watchdog.error(
            "SelfHealing",
            "Erreur inconnue non analysable.",
        )

        return {
            "success": False,
            "type": "unknown",
            "risk": "unknown",
            "message": (
                "Erreur non reconnue "
                "par SelfHealingAgent V1."
            ),
            "can_auto_fix": False,
        }

    def add_method_stub(
        self,
        file_path: str,
        class_name: str,
        method_name: str,
    ) -> dict[str, Any]:

        self.watchdog.warning(
            "SelfHealing",
            (
                "Auto-correction : ajout "
                f"méthode "
                f"{class_name}.{method_name}"
            ),
        )

        target = Path(file_path)

        if not target.exists():

            self.watchdog.error(
                "SelfHealing",
                f"Fichier introuvable : {file_path}",
            )

            return {
                "success": False,
                "error": "file_not_found",
            }

        before = target.read_text()

        backup_path = self.editor.backup(
            file_path
        )

        lines = before.splitlines()

        class_index = None

        for idx, line in enumerate(lines):

            if (
                line.strip()
                == f"class {class_name}:"
            ):
                class_index = idx
                break

        if class_index is None:

            self.watchdog.error(
                "SelfHealing",
                (
                    "Classe introuvable : "
                    f"{class_name}"
                ),
            )

            return {
                "success": False,
                "error": "class_not_found",
            }

        insert_index = len(lines)

        for idx in range(
            class_index + 1,
            len(lines),
        ):

            line = lines[idx]

            if (
                line.startswith("class ")
                and idx > class_index
            ):
                insert_index = idx
                break

        stub = [
            "",
            (
                f"    def {method_name}"
                f"(self, *args, **kwargs):"
            ),
            (
                '        """Méthode ajoutée '
                'automatiquement par '
                'SelfHealingAgent."""'
            ),
            (
                "        raise "
                "NotImplementedError("
            ),
            (
                f'            "{method_name} '
                f'doit être implémentée."'
            ),
            "        )",
            "",
        ]

        lines[insert_index:insert_index] = stub

        after = "\n".join(lines) + "\n"

        target.write_text(after)

        validation = (
            self.editor.validate_python(
                file_path
            )
        )

        diff = "\n".join(
            difflib.unified_diff(
                before.splitlines(),
                after.splitlines(),
                fromfile=(
                    f"{file_path}.before"
                ),
                tofile=(
                    f"{file_path}.after"
                ),
                lineterm="",
            )
        )

        if validation["success"]:

            self.watchdog.info(
                "SelfHealing",
                (
                    "Correction appliquée "
                    f"avec succès : "
                    f"{class_name}.{method_name}"
                ),
            )

        else:

            self.watchdog.error(
                "SelfHealing",
                (
                    "Validation Python échouée "
                    f"après correction : "
                    f"{class_name}.{method_name}"
                ),
            )

            shutil.copy(
                backup_path,
                file_path,
            )

            self.watchdog.warning(
                "SelfHealing",
                "Rollback automatique effectué",
            )

        return {
            "success": validation["success"],
            "backup": backup_path,
            "validation": validation,
            "diff": diff,
        }
