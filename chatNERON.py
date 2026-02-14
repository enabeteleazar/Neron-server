#!/usr/bin/env python3
"""
Chat interactif avec Néron AI Assistant
"""

import requests
import json
from datetime import datetime

NERON_URL = "http://localhost:8000"
MEMORY_URL = "http://localhost:8002"

def send_message(text):
    """Envoie un message à Néron"""
    try:
        response = requests.post(
            f"{NERON_URL}/input/text",
            json={"text": text},
            timeout=60
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "Pas de réponse")
    except requests.exceptions.Timeout:
        return "Timeout - Néron met trop de temps à répondre"
    except requests.exceptions.RequestException as e:
        return f"Erreur: {e}"

def get_history(limit=5):
    """Récupère l’historique des conversations"""
    try:
        response = requests.get(f"{MEMORY_URL}/retrieve?limit={limit}")
        response.raise_for_status()
        return response.json()
    except:
        return []

def search_memory(query):
    """Recherche dans la mémoire"""
    try:
        response = requests.get(f"{MEMORY_URL}/search?query={query}")
        response.raise_for_status()
        return response.json()
    except:
        return []

def print_colored(text, color="blue"):
    """Affiche du texte coloré"""
    colors = {
        "blue": "\033[0;34m",
        "green": "\033[0;32m",
        "yellow": "\033[1;33m",
        "red": "\033[0;31m",
        "reset": "\033[0m"
    }
    print(f"{colors.get(color, '')}{text}{colors['reset']}")

def main():
    print("=" * 50)
    print("CHAT AVEC NÉRON AI ASSISTANT")
    print("=" * 50)
    print("\nCommandes disponibles:")
    print("  /history  - Voir les 5 dernières conversations")
    print("  /search   - Rechercher dans l’historique")
    print("  /stats    - Statistiques de la mémoire")
    print("  /clear    - Effacer l’écran")
    print("  /quit     - Quitter")
    print("\nCommencez à taper vos messages...\n")

    while True:
        try:
            print_colored("Vous > ", "blue")
            user_input = input().strip()

            if user_input in ["/quit", "/exit", "quit", "exit"]:
                print("\nAu revoir !\n")
                break

            elif user_input == "/clear":
                print("\033[2J\033[H")
                continue

            elif user_input == "/history":
                print("\nHistorique (5 dernières):")
                history = get_history(5)
                for item in history:
                    print(f"\n[{item.get('timestamp', 'N/A')}]")
                    print(f"  Vous: {item.get('input', '')[:80]}...")
                    print(f"  Néron: {item.get('response', '')[:80]}...")
                print()
                continue

            elif user_input.startswith("/search "):
                query = user_input[8:]
                print(f"\nRecherche: {query}")
                results = search_memory(query)
                if results:
                    for item in results[:3]:
                        print(f"\n  Trouvé: {item.get('input', '')[:80]}...")
                else:
                    print("  Aucun résultat")
                print()
                continue

            elif user_input == "/stats":
                try:
                    response = requests.get(f"{MEMORY_URL}/stats")
                    stats = response.json()
                    print("\nStatistiques:")
                    print(f"  Total d'entrées: {stats.get('total_entries', 0)}")
                    print(f"  Récentes (7j): {stats.get('recent_entries_7d', 0)}")
                    print()
                except:
                    print("Impossible de récupérer les stats\n")
                continue

            if not user_input:
                continue

            print_colored("Néron > ", "yellow")
            response = send_message(user_input)
            print_colored(response, "green")
            print()

        except KeyboardInterrupt:
            print("\n\nAu revoir !\n")
            break
        except Exception as e:
            print(f"\nErreur: {e}\n")

if __name__ == "__main__":
    main()
