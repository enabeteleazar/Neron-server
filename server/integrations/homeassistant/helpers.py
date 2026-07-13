from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher


ACTION_SYNONYMS = {
    "turn_on": {"allume", "allumer", "ouvre", "ouvrir", "active", "activer", "demarre", "demarrer", "lance"},
    "turn_off": {"eteins", "eteindre", "ferme", "fermer", "desactive", "desactiver", "arrete", "coupe"},
    "toggle": {"toggle", "bascule", "inverse"},
    "lock": {"verrouille", "verrouiller"},
    "unlock": {"deverrouille", "deverrouiller"},
    "set": {"mets", "mettre", "regle", "regler", "augmente", "baisse"},
    "get_state": {"etat", "statut", "temperature", "combien", "quelle", "quel"},
    "list": {"liste", "affiche", "montre"},
}

DOMAIN_ALIASES = {
    "light": {"lumiere", "lumieres", "lampe", "lampes", "plafonnier", "spot", "eclairage"},
    "cover": {"volet", "volets", "store", "stores", "rideau", "portail", "garage"},
    "climate": {"chauffage", "thermostat", "temperature", "clim", "climatiseur"},
    "switch": {"prise", "prises", "interrupteur"},
    "lock": {"serrure", "porte", "verrou"},
    "sensor": {"capteur", "temperature", "humidite", "etat"},
    "media_player": {"tele", "tv", "musique", "radio", "spotify"},
}


def normalize(text: str) -> str:
    value = unicodedata.normalize("NFKD", (text or "").lower())
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    value = value.replace("’", " ").replace("'", " ").replace("-", " ")
    value = re.sub(r"[^a-z0-9_.:/ ]+", " ", value)
    return " ".join(value.split())


def tokens(text: str) -> list[str]:
    return [token for token in normalize(text).split() if len(token) >= 2]


def detect_action(text: str) -> str:
    query = set(tokens(text))
    for action, aliases in ACTION_SYNONYMS.items():
        if query & aliases:
            return action
    return "get_state" if {"etat", "temperature", "statut"} & query else "turn_on"


def detect_domain(text: str) -> str | None:
    query = set(tokens(text))
    for domain, aliases in DOMAIN_ALIASES.items():
        if query & aliases:
            return domain
    return None


def similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, normalize(left), normalize(right)).ratio()


def extract_number(text: str) -> float | None:
    match = re.search(r"(-?\d+(?:[,.]\d+)?)\s*(?:°|degres?)?", normalize(text))
    if not match:
        return None
    return float(match.group(1).replace(",", "."))
