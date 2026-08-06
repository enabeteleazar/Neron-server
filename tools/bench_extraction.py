#!/usr/bin/env python3
"""Banc d'essai de l'extraction memoire.

Mesure deux choses opposees sur chaque consigne :
  - le RAPPEL : combien des faits attendus sont retrouves
  - les FAUX POSITIFS : combien de faits produits ne correspondent a rien

Le cas negatif (message sans aucune information durable) sert uniquement a
mesurer la fabrication. Un tirage unique ne prouve rien : la variance entre
deux tirages identiques egale l'ecart entre deux consignes differentes.

Usage : NERON_API_KEY=... python3 tools/bench_extraction.py [tirages] [consignes...]
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import time
import unicodedata

import httpx

LLM_URL = os.getenv("NERON_LLM_URL", "http://127.0.1.2:8765").rstrip("/")
if not LLM_URL.endswith("/llm"):
    LLM_URL += "/llm"
API_KEY = os.getenv("NERON_API_KEY", "")

LISTE_13 = ("a_pour_frere, a_pour_soeur, a_pour_enfant, a_pour_conjoint, a_pour_parent,\n"
            "prenom, habite_a, travaille_a, metier, aime, n_aime_pas, possede, autre")

# ── Cas de test : (message, faits attendus) ──────────────────────────────────
# Un attendu = (libelle, predicats acceptes, fragment attendu dans objet/sujet)
CAS = {
    "julien": {
        "message": ("Mon frere Julien est kine a Bordeaux, il deteste le cafe "
                    "et son film prefere est Interstellar."),
        "attendus": [
            ("fraternite", {"a_pour_frere", "a_pour_soeur"}, "julien"),
            ("metier",     {"metier", "travaille_a", "profession"}, "kin"),
            ("ville",      {"habite_a", "travaille_a", "vit_a"}, "bordeaux"),
            ("cafe",       {"n_aime_pas", "deteste"}, "caf"),
            ("film",       {"film_prefere", "aime"}, "interstellar"),
        ],
    },
    # Cas NEGATIF : que de l'ephemere. La bonne reponse est une liste vide.
    "cinema": {
        "message": ("Ce soir je vais au cinema de Troyes avec Absalon voir "
                    "le film Spiderman a 21 heures."),
        "attendus": [],
    },
}

CONSIGNES = {
    "v5_courte_13": """Extrais les informations durables de ce message.

Le predicat doit OBLIGATOIREMENT etre choisi dans cette liste :
{liste}

Regles :
- un objet JSON par information ATOMIQUE : le metier et la ville sont deux faits distincts
- le sujet est utilisateur, ou le prenom de la personne concernee
- l objet est une valeur courte, jamais une phrase
- n invente rien qui ne soit pas ecrit dans le message

Reponds en JSON, cle facts, liste d objets ayant les cles subject, predicate, object.

Message : {message}""",

    "v8_vide_autorise": """Extrais les informations durables de ce message.

Beaucoup de messages ne contiennent AUCUNE information durable : ils parlent
d une activite ponctuelle, d un projet du soir, d un rendez-vous. Dans ce cas
la bonne reponse est une liste facts VIDE. C est une reponse correcte et
attendue, pas un echec.

Le predicat doit OBLIGATOIREMENT etre choisi dans cette liste :
{liste}

Regles :
- un objet JSON par information ATOMIQUE : le metier et la ville sont deux faits distincts
- le sujet est utilisateur, ou le prenom de la personne concernee
- l objet est une valeur courte, jamais une phrase
- n invente rien qui ne soit pas ecrit dans le message

Reponds en JSON, cle facts, liste d objets ayant les cles subject, predicate, object.

Message : {message}""",
}


def plat(texte: str) -> str:
    sans = unicodedata.normalize("NFD", texte.lower())
    return "".join(c for c in sans if unicodedata.category(c) != "Mn")


def un_tirage(prompt: str) -> tuple[list[dict], float, str | None]:
    if not API_KEY:
        return [], 0.0, "NERON_API_KEY absente de l environnement"
    t0 = time.monotonic()
    try:
        r = httpx.post(
            f"{LLM_URL}/generate",
            json={"task_type": "memory", "json_mode": True, "prompt": prompt},
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=900.0,
        )
    except Exception as exc:
        return [], time.monotonic() - t0, f"appel impossible : {exc}"
    duree = time.monotonic() - t0
    if r.status_code != 200:
        return [], duree, f"HTTP {r.status_code}"
    try:
        faits = json.loads(r.json()["result"]).get("facts", [])
        return (faits if isinstance(faits, list) else []), duree, None
    except Exception as exc:
        return [], duree, f"JSON illisible : {exc}"


def note(faits: list[dict], attendus: list) -> tuple[set[str], int]:
    """Renvoie (libelles retrouves, nombre de faits ne correspondant a rien)."""
    trouves: set[str] = set()
    apparies: set[int] = set()
    for libelle, predicats, fragment in attendus:
        cibles = {plat(x) for x in predicats}
        for i, f in enumerate(faits):
            p = plat(str(f.get("predicate", "")))
            texte = plat(str(f.get("object", ""))) + " " + plat(str(f.get("subject", "")))
            if p in cibles and fragment in texte:
                trouves.add(libelle)
                apparies.add(i)
                break
    return trouves, len(faits) - len(apparies)


def main() -> None:
    if not API_KEY:
        sys.exit("NERON_API_KEY absente de l environnement")
    tirages = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    choisis = sys.argv[2:] or list(CONSIGNES)
    inconnus = [n for n in choisis if n not in CONSIGNES]
    if inconnus:
        sys.exit(f"consigne(s) inconnue(s) : {', '.join(inconnus)}")

    total = len(choisis) * len(CAS) * tirages
    print(f"{len(choisis)} consigne(s) x {len(CAS)} cas x {tirages} tirage(s) "
          f"= {total} appels — comptez environ {total * 3} minutes\n")

    for nom in choisis:
        print(f"══ {nom} " + "═" * (48 - len(nom)))
        for cas, donnees in CAS.items():
            prompt = CONSIGNES[nom].format(liste=LISTE_13, message=donnees["message"])
            attendus = donnees["attendus"]
            rappels, faux, durees, jamais = [], [], [], None
            for i in range(1, tirages + 1):
                faits, duree, err = un_tirage(prompt)
                if err:
                    print(f"  {cas} tirage {i} : ECHEC — {err}")
                    continue
                trouves, fp = note(faits, attendus)
                rappels.append(len(trouves))
                faux.append(fp)
                durees.append(duree)
                jamais = trouves if jamais is None else (jamais & trouves)
                print(f"  {cas} tirage {i} : {len(trouves)}/{len(attendus)} attendus, "
                      f"{fp} faux, {len(faits)} produits, {duree:.0f}s")
            if rappels:
                print(f"  → {cas} : rappel {statistics.mean(rappels):.1f}/{len(attendus)}, "
                      f"faux positifs {statistics.mean(faux):.1f}, "
                      f"latence {statistics.mean(durees):.0f}s, "
                      f"toujours trouves : {', '.join(sorted(jamais)) or 'aucun'}")
        print()


if __name__ == "__main__":
    main()
