# tools/twilio_tool.py
# Néron — Outil d'appel vocal via Twilio

import logging
from twilio.rest import Client
from config import settings

logger = logging.getLogger("twilio_tool")


def _get_client() -> Client:
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        raise ValueError("Twilio non configuré — vérifiez neron.yaml")
    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def call(message: str, to: str = None) -> dict:
    """Passe un appel vocal avec un message TTS Twilio."""
    if not settings.TWILIO_ENABLED:
        return {"ok": False, "error": "Twilio désactivé dans neron.yaml"}

    to_number = to or settings.TWILIO_TO
    if not to_number:
        return {"ok": False, "error": "Numéro de destination manquant"}

    try:
        client = _get_client()
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="fr-FR" voice="Polly.Lea">{message}</Say>
    <Pause length="1"/>
    <Say language="fr-FR" voice="Polly.Lea">Fin du message de Néron.</Say>
</Response>"""

        call_obj = client.calls.create(
            twiml=twiml,
            to=to_number,
            from_=settings.TWILIO_FROM
        )
        logger.info(f"Appel Twilio lancé — SID: {call_obj.sid} → {to_number}")
        return {"ok": True, "sid": call_obj.sid}

    except Exception as e:
        logger.error(f"Erreur appel Twilio : {e}")
        return {"ok": False, "error": str(e)}


def sms(message: str, to: str = None) -> dict:
    """Envoie un SMS."""
    if not settings.TWILIO_ENABLED:
        return {"ok": False, "error": "Twilio désactivé"}

    to_number = to or settings.TWILIO_TO
    try:
        client = _get_client()
        msg = client.messages.create(
            body=message[:1600],
            to=to_number,
            from_=settings.TWILIO_FROM
        )
        logger.info(f"SMS Twilio envoyé — SID: {msg.sid}")
        return {"ok": True, "sid": msg.sid}
    except Exception as e:
        logger.error(f"Erreur SMS Twilio : {e}")
        return {"ok": False, "error": str(e)}
