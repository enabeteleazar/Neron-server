# core/pipeline/nlp/intent_classifier.py
# v2.2 — Classifier NLP compatible avec nlp_processor.py

from __future__ import annotations

import unicodedata
from typing import Dict


def _normalize(text: str) -> str:
    n = unicodedata.normalize("NFD", text.lower().strip())
    n = "".join(c for c in n if unicodedata.category(c) != "Mn")
    return n.replace("'", " ").replace("’", " ").replace("`", " ")


_RULES: Dict[str, list[str]] = {
    "system_status": [
        "statut systeme",
        "etat systeme",
        "status systeme",
        "liste les services",
        "services actifs",
        "services systemd",
        "quels services tournent",
        "services en cours",
        "verifie les services",
    ],

    "network_status": [
        "ports ouverts",
        "ports reseau",
        "connexions reseau",
        "etat reseau",
        "status reseau",
        "ss -tulpn",
        "netstat",
    ],

    "time_query": [
        "quelle heure",
        "donne l heure",
        "il est quelle heure",
        "date actuelle",
        "date du jour",
    ],

    "ha_action": [
        "allume",
        "eteins",
        "éteins",
        "active",
        "desactive",
        "désactive",
        "lumiere",
        "lampes",
    ],

    "news_query": [
        "actualite",
        "actualites",
        "news",
        "dernieres nouvelles",
    ],

    "weather_query": [
        "meteo",
        "météo",
        "temps aujourd hui",
        "temperature",
    ],

    "todo_action": [
        "ajoute une tache",
        "liste mes taches",
        "todo",
        "rappel",
    ],

    "wiki_query": [
        "c est quoi",
        "qui est",
        "definition",
        "définition",
        "explique moi",
    ],

    "code": [
        "code",
        "script",
        "python",
        "bash",
        "fonction",
    ],

    "code_audit": [
        "analyse ce code",
        "audite ce code",
        "corrige ce code",
        "bug",
        "erreur python",
    ],

    "web_search": [
        "cherche sur internet",
        "recherche web",
        "sur le web",
    ],

    "personality_feedback": [
        "parle plus",
        "sois plus",
        "reponds plus",
        "réponds plus",
    ],
}


def scores_all(text: str) -> Dict[str, float]:
    q = _normalize(text)
    scores: Dict[str, float] = {}

    for intent, patterns in _RULES.items():
        score = 0.0

        for pattern in patterns:
            p = _normalize(pattern)
            if p in q:
                score += 1.0

        if score > 0:
            scores[intent] = min(0.40 + score * 0.25, 1.0)

    if not scores:
        scores["conversation"] = 0.40

    return scores


def classify(text: str) -> tuple[str, float]:
    scores = scores_all(text)
    intent = max(scores, key=scores.get)
    confidence = scores[intent]

    if confidence < 0.40:
        return "conversation", confidence

    return intent, confidence
