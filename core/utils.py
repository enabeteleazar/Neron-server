# core/utils.py
# Fonctions utilitaires communes à tout le projet Neron

import unicodedata
from typing import Any, Dict, List, Optional


def normalize_text(text: str) -> str:
    """
    Normalise le texte pour l'intent routing et la recherche.
    Supprime les accents et met en minuscules.
    """
    n = unicodedata.normalize("NFD", text.lower().strip())
    return "".join(c for c in n if unicodedata.category(c) != "Mn")


def safe_get(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """
    Accès sécurisé aux données imbriquées dans un dict.
    Equivalent à data.get(keys[0], {}).get(keys[1], {}).get(keys[2], default)
    """
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return default
    return current if current is not None else default


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Tronque le texte à une longueur maximale avec suffixe.
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_duration(seconds: float) -> str:
    """
    Formate une durée en secondes en format lisible.
    """
    if seconds < 1:
        return ".1fs"
    elif seconds < 60:
        return ".1f"
    elif seconds < 3600:
        return ".1f"
    else:
        return ".1f"


def validate_api_key_format(api_key: str) -> bool:
    """
    Valide le format d'une API key (doit être alphanumérique).
    """
    return bool(api_key and api_key.replace("-", "").replace("_", "").isalnum())


def clean_filename(filename: str) -> str:
    """
    Nettoie un nom de fichier pour éviter les caractères dangereux.
    """
    import re
    return re.sub(r'[^\w\-_\.]', '_', filename)


def get_file_size_mb(filepath: str) -> float:
    """
    Retourne la taille d'un fichier en MB.
    """
    import os
    try:
        return os.path.getsize(filepath) / (1024 * 1024)
    except OSError:
        return 0.0


def ensure_dir(path: str) -> None:
    """
    Crée le répertoire s'il n'existe pas.
    """
    import os
    os.makedirs(path, exist_ok=True)


def is_valid_python_file(filepath: str) -> bool:
    """
    Vérifie si le fichier est un fichier Python valide.
    """
    import os
    return (
        os.path.isfile(filepath) and
        filepath.endswith('.py') and
        os.access(filepath, os.R_OK)
    )


def count_lines_in_file(filepath: str) -> int:
    """
    Compte le nombre de lignes dans un fichier.
    """
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def get_memory_usage_mb() -> float:
    """
    Retourne l'usage mémoire du processus actuel en MB.
    """
    import psutil
    import os
    try:
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)
    except Exception:
        return 0.0


def format_bytes(bytes_value: int) -> str:
    """
    Formate des bytes en format lisible (KB, MB, GB).
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_value < 1024.0:
            return ".1f"
        bytes_value /= 1024.0
    return ".1f"


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """
    Charge du JSON en sécurité avec gestion d'erreur.
    """
    import json
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(data: Any, default: str = "{}") -> str:
    """
    Sérialise en JSON en sécurité avec gestion d'erreur.
    """
    import json
    try:
        return json.dumps(data, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return default