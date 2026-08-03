#!/usr/bin/env python3
"""Banc d'essai de l'extraction memoire.

Lance chaque consigne candidate N fois sur la meme phrase, compte les faits
attendus retrouves et affiche des moyennes. Existe parce qu'un tirage unique
ne dit rien : la variance entre deux tirages identiques est du meme ordre
que l'ecart entre deux consignes.

Usage : NERON_API_KEY=... python3 tools/bench_extraction.py [nb_tirages]
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

MESSAGE = ("Mon frere Julien est kine a Bordeaux, il deteste le cafe "
           "et son film prefere est Interstellar.")

# (libelle, predicats acceptes, fragment attendu dans l'objet)
ATTENDUS = [
    ("fraternite", {"a_pour_frere", "a_pour_soeur"}, "julien"),
    ("metier",     {"metier", "travaille_a", "profession"}, "kin"),
    ("ville",      {"habite_a", "travaille_a", "vit_a"}, "bordeaux"),
    ("cafe",       {"n_aime_pas", "deteste"}, "caf"),
    ("film",       {"film_prefere", "aime"}, "interstellar"),
]

LISTE_13 = ("a_pour_frere, a_pour_soeur, a_pour_enfant, a_pour_conjoint, a_pour_parent,\n"
            "prenom, habite_a, travaille_a, metier, aime, n_aime_pas, possede, autre")
LISTE_15 = ("a_pour_frere, a_pour_soeur, a_pour_enfant, a_pour_conjoint, a_pour_parent,\n"
            "prenom, habite_a, travaille_a, metier, aime, n_aime_pas,\n"
            "film_prefere, animal_prefere, possede, autre")

CANDIDATS = {
    "v5_courte_13": f"""Extrais les informations durables de ce message.

Le predicat doit OBLIGATOIREMENT etre choisi dans cette liste :
{LISTE_13}

Regles :
- un objet JSON par information ATOMIQUE : le metier et la ville sont deux faits distincts
- le sujet est utilisateur, ou le prenom de la personne concernee
- l objet est une valeur courte, jamais une phrase
- n invente rien qui ne soit pas ecrit dans le message

Reponds en JSON, cle facts, liste d objets ayant les cles subject, predicate, object.

Message : {MESSAGE}""",

    "v6_schema_15": f"""Extrais les informations durables de ce message.

Un message peut produire PLUSIEURS faits. Chaque fait contient UNE seule information.

Le predicat doit etre choisi dans cette liste :
{LISTE_15}

La personne qui parle se nomme exactement utilisateur.
N invente rien qui ne soit pas ecrit dans le message.

Structure exacte de la reponse :
{{"facts": [{{"subject": "...", "predicate": "...", "object": "..."}}]}}

Message : {MESSAGE}""",

    "v7_courte_13_parente": f"""Extrais les informations durables de ce message.

Le predicat doit OBLIGATOIREMENT etre choisi dans cette liste :
{LISTE_13}

Regles :
- indique toujours le lien de parente entre utilisateur et les personnes citees
- un objet JSON par information ATOMIQUE : le metier et la ville sont deux faits distincts
- le sujet est utilisateur, ou le prenom de la personne concernee
- l objet est une valeur courte, jamais une phrase
- n invente rien qui ne soit pas ecrit dans le message

Reponds en JSON, cle facts, liste d objets ayant les cles subject, predicate, object.

Message : {MESSAGE}""",
}


def plat(texte: str) -> str:
    """Minuscules sans accents, pour comparer sans piege."""
    sans = unicodedata.normalize("NFD", texte.lower())
    return "".join(c for c in sans if unicodedata.category(c) != "Mn")


def un_tirage(prompt: str) -> tuple[list[dict], float, str | None]:
    t0 = time.monotonic()
    r = httpx.post(
        f"{LLM_URL}/generate",
        json={"task_type": "memory", "json_mode": True, "prompt": prompt},
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=600.0,
    )
    duree = time.monotonic() - t0
    if r.status_code != 200:
        return [], duree, f"HTTP {r.status_code}"
    try:
        brut = r.json()["result"]
        faits = json.loads(brut).get("facts", [])
        return (faits if isinstance(faits, list) else []), duree, None
    except Exception as exc:
        return [], duree, f"JSON illisible : {exc}"


def note(faits: list[dict]) -> tuple[set[str], int]:
    trouves: set[str] = set()
    for libelle, predicats, fragment in ATTENDUS:
        for f in faits:
            p = plat(str(f.get("predicate", "")))
            o = plat(str(f.get("object", "")))
            s = plat(str(f.get("subject", "")))
            if p in {plat(x) for x in predicats} and (fragment in o or fragment in s):
                trouves.add(libelle)
                break
    return trouves, len(faits)


def main() -> None:
    if not API_KEY:
        sys.exit("NERON_API_KEY absente de l environnement")
    tirages = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    choisis = sys.argv[2:] or list(CANDIDATS)
    inconnus = [n for n in choisis if n not in CANDIDATS]
    if inconnus:
        sys.exit(f"consigne(s) inconnue(s) : {', '.join(inconnus)}")

    print(f"{len(choisis)} consigne(s) x {tirages} tirage(s) — "
          f"comptez environ {len(choisis) * tirages * 3} minutes\n")

    for nom in choisis:
        prompt = CANDIDATS[nom]
        scores, totaux, durees, jamais = [], [], [], None
        print(f"── {nom} " + "─" * (50 - len(nom)))
        for i in range(1, tirages + 1):
            faits, duree, err = un_tirage(prompt)
            if err:
                print(f"  tirage {i} : ECHEC — {err}")
                continue
            trouves, total = note(faits)
            scores.append(len(trouves))
            totaux.append(total)
            durees.append(duree)
            jamais = trouves if jamais is None else (jamais & trouves)
            manquants = [l for l, _, _ in ATTENDUS if l not in trouves]
            print(f"  tirage {i} : {len(trouves)}/5 attendus, {total} faits produits, "
                  f"{duree:.0f}s — manque : {', '.join(manquants) or 'rien'}")
        if scores:
            print(f"  MOYENNE {statistics.mean(scores):.1f}/5  "
                  f"(min {min(scores)}, max {max(scores)})  "
                  f"faits produits {statistics.mean(totaux):.1f}  "
                  f"latence {statistics.mean(durees):.0f}s")
            print(f"  toujours trouves : {', '.join(sorted(jamais)) or 'aucun'}\n")


if __name__ == "__main__":
    main()
