#!/usr/bin/env python3
"""
Client CLI Néron vNext++
- API Key
- Streaming robuste
- Memory injectée automatiquement
- Retry + fallback
- Debug mode
"""

import requests
import json
import os
import time

# =========================
# CONFIG
# =========================

NERON_URL = os.getenv("NERON_URL", "http://100.90.194.109:8010")
MEMORY_URL = os.getenv("MEMORY_URL", "http://100.90.194.109:8002")

NERON_API_KEY = os.getenv("NERON_API_KEY", "dev-key")

DEBUG = os.getenv("NERON_DEBUG", "0") == "1"

TIMEOUT = 60
RETRIES = 2


def debug(msg):
    if DEBUG:
        print(f"[DEBUG] {msg}")


def get_headers():
    return {
        "Authorization": f"Bearer {NERON_API_KEY}",
        "Content-Type": "application/json"
    }


# =========================
# MEMORY CONTEXT BUILDER
# =========================

def build_context(user_input):
    """
    Injecte automatiquement de la mémoire pertinente
    """
    try:
        r = requests.get(
            f"{MEMORY_URL}/search",
            params={"query": user_input},
            headers=get_headers(),
            timeout=3
        )

        if r.status_code != 200:
            return ""

        results = r.json()

        context = "\n".join([
            f"- {item.get('input', '')} -> {item.get('response', '')}"
            for item in results[:3]
        ])

        if context:
            return f"\n[Contexte mémoire]\n{context}\n"

        return ""

    except:
        return ""


# =========================
# CORE API
# =========================

def health_check():
    try:
        r = requests.get(
            f"{NERON_URL}/health",
            headers=get_headers(),
            timeout=3
        )
        return r.status_code == 200
    except:
        return False


def send_message(text, stream=True):
    """
    Envoi avec:
    - retry
    - fallback endpoint
    - contexte mémoire
    """

    context = build_context(text)
    payload = {"text": context + text}

    endpoints = ["/input/text", "/input"] if stream else ["/input"]

    for attempt in range(RETRIES):
        for endpoint in endpoints:
            try:
                debug(f"POST {endpoint} (attempt {attempt})")

                if stream and endpoint == "/input/text":
                    with requests.post(
                        f"{NERON_URL}{endpoint}",
                        json=payload,
                        headers=get_headers(),
                        stream=True,
                        timeout=TIMEOUT
                    ) as r:
                        r.raise_for_status()

                        full = ""

                        for chunk in r.iter_lines():
                            if not chunk:
                                continue

                            decoded = chunk.decode("utf-8").strip()

                            # Support SSE
                            if decoded.startswith("data:"):
                                decoded = decoded[5:].strip()

                            try:
                                data = json.loads(decoded)
                                token = data.get("token") or data.get("response", "")
                            except:
                                token = decoded

                            print(token, end="", flush=True)
                            full += token

                        print()
                        return full

                else:
                    r = requests.post(
                        f"{NERON_URL}{endpoint}",
                        json=payload,
                        headers=get_headers(),
                        timeout=TIMEOUT
                    )
                    r.raise_for_status()

                    data = r.json()
                    response = data.get("response", "")

                    print(response)
                    return response

            except requests.exceptions.Timeout:
                debug("Timeout...")
                continue

            except requests.exceptions.ConnectionError:
                debug("Connection error...")
                continue

            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code == 401:
                    return "\n[AUTH ERROR] API key invalide"
                debug(f"HTTP error: {e}")
                continue

    return "\n[ERROR] Néron indisponible après retries"


# =========================
# MEMORY API
# =========================

def get_history(limit=5):
    try:
        r = requests.get(
            f"{MEMORY_URL}/retrieve",
            params={"limit": limit},
            headers=get_headers(),
            timeout=5
        )
        r.raise_for_status()
        return r.json()
    except:
        return []


def get_stats():
    try:
        r = requests.get(
            f"{MEMORY_URL}/stats",
            headers=get_headers(),
            timeout=5
        )
        r.raise_for_status()
        return r.json()
    except:
        return None


# =========================
# UI
# =========================

def print_colored(text, color="blue", end="\n"):
    colors = {
        "blue": "\033[0;34m",
        "green": "\033[0;32m",
        "yellow": "\033[1;33m",
        "red": "\033[0;31m",
        "reset": "\033[0m"
    }
    print(f"{colors.get(color, '')}{text}{colors['reset']}", end=end)


# =========================
# MAIN LOOP
# =========================

def main():
    print("=" * 50)
    print("NÉRON CLIENT vNEXT++")
    print("=" * 50)

    if health_check():
        print_colored("[OK] neron-server en ligne", "green")
    else:
        print_colored("[KO] serveur indisponible", "red")

    print("""
Commandes:
  /history
  /stats
  /health
  /debug on|off
  /quit
""")

    global DEBUG

    while True:
        try:
            print_colored("Vous > ", "blue", end="")
            user_input = input().strip()

            if not user_input:
                continue

            if user_input in ["/quit", "/exit"]:
                break

            elif user_input == "/health":
                print_colored("OK" if health_check() else "KO",
                              "green" if health_check() else "red")
                continue

            elif user_input == "/history":
                for item in get_history():
                    print(f"\n[{item.get('timestamp')}]")
                    print(f"Vous : {item.get('input')[:80]}")
                    print(f"Néron: {item.get('response')[:80]}")
                print()
                continue

            elif user_input == "/stats":
                stats = get_stats()
                print(stats if stats else "Erreur")
                continue

            elif user_input.startswith("/debug"):
                DEBUG = "on" in user_input
                print(f"DEBUG = {DEBUG}")
                continue

            print_colored("Néron > ", "yellow", end="")
            send_message(user_input, stream=True)

        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
