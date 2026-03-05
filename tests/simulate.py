#!/usr/bin/env python3
# simulate.py - Simulation multi-modeles Neron AI

import random
import re
import requests
import subprocess
import time
from datetime import datetime

NERON_URL = "http://localhost:8000/input/text"
HEALTH_URL = "http://localhost:8000/health"
ENV_FILE = "/opt/Neron_AI/.env"
TIMEOUT = 120
PAUSE = 2
TOURS = 5
LLM_STARTUP_WAIT = 20  # secondes apres restart neron_llm

MODELES = [
    "llama3.2:1b",
    "llama3.2:3b",
    "phi3",
    "tinyllama",
    "orca-mini",
    "gemma:2b",
    "gemma3:4b",
]

PHRASES = [
    "Bonjour Neron, comment ca va ?",
    "Quelle heure est-il ?",
    "Raconte-moi une blague",
    "Explique ce qu est l intelligence artificielle",
    "Qui est le president de la France ?",
    "Quelles sont les dernieres nouvelles en technologie ?",
]


def run(cmd: str) -> tuple:
    result = subprocess.run(
        cmd, shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    return result.returncode, result.stdout.strip()


def modele_disponible(modele: str) -> bool:
    """Verifie si le modele est telecharge dans Ollama."""
    _, out = run("docker exec neron_ollama ollama list")
    # Normaliser : "llama3.2:3b" matche "llama3.2:3b" dans la liste
    nom = modele.split(":")[0]
    tag = modele.split(":")[1] if ":" in modele else "latest"
    return modele in out or nom in out


def changer_modele(modele: str):
    """Modifie OLLAMA_MODEL dans .env."""
    with open(ENV_FILE, "r") as f:
        contenu = f.read()
    contenu = re.sub(
        r"^OLLAMA_MODEL=.*$",
        f"OLLAMA_MODEL={modele}",
        contenu,
        flags=re.MULTILINE
    )
    with open(ENV_FILE, "w") as f:
        f.write(contenu)
    print(f"  .env mis a jour : OLLAMA_MODEL={modele}")


def redemarrer_llm():
    """Stoppe et relance neron_llm avec le nouveau modele."""
    print("  Arret de neron_llm...")
    run("docker stop neron_llm")
    time.sleep(2)
    print("  Demarrage de neron_llm...")
    run("cd /mnt/usb-storage/Neron_AI && docker compose up -d neron_llm")
    print(f"  Attente {LLM_STARTUP_WAIT}s...", end="", flush=True)
    time.sleep(LLM_STARTUP_WAIT)
    print(" OK")


def attendre_core(timeout: int = 10) -> bool:
    """Attend que neron_core soit joignable."""
    debut = time.monotonic()
    while time.monotonic() - debut < timeout:
        try:
            r = requests.get(HEALTH_URL, timeout=3)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


def envoyer(phrase: str) -> dict:
    try:
        r = requests.post(NERON_URL, json={"text": phrase}, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.Timeout:
        return {"error": "timeout", "response": "Neron n a pas repondu a temps", "execution_time_ms": 0}
    except requests.exceptions.ConnectionError:
        return {"error": "connexion", "response": "Impossible de joindre Neron", "execution_time_ms": 0}
    except Exception as e:
        return {"error": str(e), "response": "Erreur inconnue", "execution_time_ms": 0}


def simuler_modele(modele: str) -> dict:
    log_file = f"conversation_{modele.replace(':', '_')}.txt"
    resultats = []

    print(f"\n{'=' * 60}")
    print(f"  Modele : {modele}")
    print(f"{'=' * 60}\n")

    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"# Simulation Neron AI - modele {modele}\n")
        f.write(f"# Date : {datetime.now().isoformat()}\n")
        f.write(f"# Tours : {TOURS}\n\n")

        for i in range(TOURS):
            phrase = random.choice(PHRASES)
            print(f"Tour {i + 1}/{TOURS}")
            print(f"  Vous  : {phrase}")

            debut = time.monotonic()
            data = envoyer(phrase)
            duree = round((time.monotonic() - debut) * 1000, 2)

            response = data.get("response", "Pas de reponse")
            intent = data.get("intent", "?")
            agent = data.get("agent", "?")
            ms = data.get("execution_time_ms", 0)
            error = data.get("error")

            print(f"  Neron : {response}")
            print(f"  Intent: {intent} | Agent: {agent} | {ms}ms | {'ERR' if error else 'OK'}\n")

            now = datetime.now().isoformat()
            f.write(f"--- Tour {i + 1} ---\n")
            f.write(f"[{now}] Vous  : {phrase}\n")
            f.write(f"[{now}] Neron : {response}\n")
            f.write(f"[{now}] Intent: {intent} | Agent: {agent} | {ms}ms\n")
            f.write(f"[{now}] Duree client: {duree}ms\n\n")

            resultats.append({
                "intent": intent,
                "ms": ms,
                "error": error
            })

            if i < TOURS - 1:
                time.sleep(PAUSE)

        erreurs = sum(1 for r in resultats if r["error"])
        ms_vals = [r["ms"] for r in resultats if r["ms"]]
        avg_ms = round(sum(ms_vals) / len(ms_vals), 2) if ms_vals else 0
        intents = {}
        for r in resultats:
            intents[r["intent"]] = intents.get(r["intent"], 0) + 1

        resume = (
            f"\n--- Resume modele {modele} ---\n"
            f"Tours    : {TOURS}\n"
            f"Erreurs  : {erreurs}\n"
            f"Lat. moy.: {avg_ms}ms\n"
            f"Intents  : {intents}\n"
        )
        print(resume)
        f.write(resume)

    print(f"Log sauvegarde : {log_file}")
    return {"modele": modele, "erreurs": erreurs, "avg_ms": avg_ms}


def main():
    print("\n" + "=" * 60)
    print("  Simulation Neron AI - Multi-Modeles")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    if not attendre_core():
        print("ERREUR : Neron Core inaccessible sur localhost:8000")
        return

    tous_resultats = []
    modeles_sautes = []

    for modele in MODELES:
        print(f"\n>>> Preparation modele : {modele}")

        # Verifier que le modele est disponible
        if not modele_disponible(modele):
            print(f"  SKIP : modele `{modele}` non telecharge dans Ollama")
            modeles_sautes.append(modele)
            continue

        changer_modele(modele)
        redemarrer_llm()
        resultat = simuler_modele(modele)
        tous_resultats.append(resultat)

    # Resume global
    print("\n" + "=" * 60)
    print("  Resume global")
    print("=" * 60)
    for r in tous_resultats:
        print(f"  {r['modele']:20} | Erreurs: {r['erreurs']} | Lat. moy.: {r['avg_ms']}ms")

    if modeles_sautes:
        print(f"\n  Modeles sautes (non disponibles) : {', '.join(modeles_sautes)}")

    print()


if __name__ == "__main__":
    main()
