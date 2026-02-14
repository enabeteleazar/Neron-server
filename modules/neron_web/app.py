import gradio as gr
import requests

NERON_CORE_URL = "http://neron-core:8000"

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
        
    except requests.exceptions.RequestException as e:
        return f"❌ Erreur réseau: {str(e)}"
    except Exception as e:
        return f"❌ Erreur: {str(e)}"


# Interface simple
demo = gr.ChatInterface(
    chat,
    title="🧠 Néron - Assistant IA",
    description="Propulsé par Ollama.",
    theme=gr.themes.Soft()
)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
