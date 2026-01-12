from neron.models.message import NeronMessage

class Orchestrator:
    def handle(self, message: NeronMessage) -> NeronMessage:
        # Logique de traitement du message
        # V1 Reponse echo simple
        response_text = f"Message bien reçu: {message.content}"
        return NeronMessage(
            source="core",
            target=message.source,
            content=response_text
        )