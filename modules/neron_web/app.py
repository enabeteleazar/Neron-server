import gradio as gr
import requests
import os

# Utiliser l'IP de l'hôte ou le nom du service Docker
NERON_CORE_URL = os.getenv("NERON_CORE_URL", "http://192.168.1.130:8000")

def chat(message, history):
    """Envoie le message à Néron"""
    try:
        response = requests.post(
            f"{NERON_CORE_URL}/input/text",
            json={"text": message},
            timeout=120
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "Erreur: pas de réponse")
        
    except requests.exceptions.Timeout:
        return "⏱️ Timeout: Néron met trop de temps à répondre (>2min)"
    except requests.exceptions.ConnectionError:
        return f"❌ Erreur de connexion: Impossible de joindre Néron à {NERON_CORE_URL}"
    except requests.exceptions.RequestException as e:
        return f"❌ Erreur réseau: {str(e)}"
    except Exception as e:
        return f"❌ Erreur: {str(e)}"


# Interface simple
demo = gr.ChatInterface(
    chat,
    title="🧠 Néron - Assistant IA",
    description=f"Propulsé par Ollama • Connecté à {NERON_CORE_URL}",
    theme=gr.themes.Soft(),
    examples=[
        "Bonjour Néron, comment vas-tu ?",
        "Explique-moi la photosynthèse",
        "Raconte-moi une blague",
        "Quelle est la capitale de la France ?",
    ],
    retry_btn="🔄 Réessayer",
    undo_btn="↩️ Annuler",
    clear_btn="🗑️ Effacer",
)

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )
