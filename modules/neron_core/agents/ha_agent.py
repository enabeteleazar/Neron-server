# agents/ha_agent.py
# Neron Core - Agent Home Assistant (REST API directe)

import httpx
import unicodedata
from agents.base_agent import BaseAgent, AgentResult
from config import settings

HA_URL     = getattr(settings, "HA_URL", "http://homeassistant.local:8123")
HA_TOKEN   = getattr(settings, "HA_TOKEN", "")
HA_ENABLED = getattr(settings, "HA_ENABLED", False)
HA_TIMEOUT = 10.0

# --- Mapping actions ---
TURN_ON_KEYS  = ["allume", "active", "ouvre", "demarre", "mets"]
TURN_OFF_KEYS = ["eteins", "desactive", "ferme", "arrete", "coupe"]

# Domaines HA par entité
DOMAIN_MAP = {
    "lumiere":     "light",
    "lampe":       "light",
    "plafonnier":  "light",
    "led":         "light",
    "volet":       "cover",
    "store":       "cover",
    "rideau":      "cover",
    "thermostat":  "climate",
    "chauffage":   "climate",
    "climatiseur": "climate",
    "prise":       "switch",
    "interrupteur":"switch",
    "ventilateur": "fan",
    "alarme":      "alarm_control_panel",
    "scene":       "scene",
}

# Pièces connues
ROOM_MAP = {
    "salon":        "salon",
    "cuisine":      "cuisine",
    "chambre":      "chambre",
    "salle de bain":"salle_de_bain",
    "bureau":       "bureau",
    "couloir":      "couloir",
    "garage":       "garage",
    "jardin":       "jardin",
    "entree":       "entree",
    "cave":         "cave",
}


def _normalize(text: str) -> str:
    """Supprime les accents et met en minuscules"""
    text = unicodedata.normalize("NFD", text.lower().strip())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _parse_query(query: str) -> dict:
    """
    Parse la requête pour extraire action, domaine, entité, pièce.
    Retourne un dict avec les infos extraites.
    """
    q = _normalize(query)

    # Action
    action = "turn_on"
    for k in TURN_OFF_KEYS:
        if k in q:
            action = "turn_off"
            break

    # Domaine HA
    domain = "light"  # défaut
    domain_label = "lumière"
    for label, ha_domain in DOMAIN_MAP.items():
        if label in q:
            domain = ha_domain
            domain_label = label
            break

    # Pièce
    room = None
    room_label = None
    for label, room_id in ROOM_MAP.items():
        if label in q:
            room = room_id
            room_label = label
            break

    # Entity ID — ex: light.salon, light.chambre
    if room:
        entity_id = f"{domain}.{room}"
    else:
        entity_id = f"{domain}.{domain_label.replace(' ', '_')}"

    return {
        "action": action,
        "domain": domain,
        "entity_id": entity_id,
        "domain_label": domain_label,
        "room": room,
        "room_label": room_label,
    }


def _build_response(parsed: dict) -> str:
    """Construit la réponse textuelle après exécution"""
    action_label = "allumé" if parsed["action"] == "turn_on" else "éteint"

    if parsed["domain"] == "cover":
        action_label = "ouvert" if parsed["action"] == "turn_on" else "fermé"
    elif parsed["domain"] == "climate":
        action_label = "activé" if parsed["action"] == "turn_on" else "désactivé"

    entity = parsed["domain_label"]
    room = f" du {parsed['room_label']}" if parsed["room_label"] else ""

    return f"J'ai {action_label} la {entity}{room}."


class HAAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="ha_agent")
        self._headers = {
            "Authorization": f"Bearer {HA_TOKEN}",
            "Content-Type": "application/json",
        }

    async def execute(self, query: str, **kwargs) -> AgentResult:
        if not HA_ENABLED:
            return self._failure("Home Assistant non activé — configurez : make ha-setup")

        if not HA_TOKEN:
            return self._failure("Token Home Assistant manquant dans neron.yaml")

        self.logger.info(f"HA action pour : {repr(query)}")
        start = self._timer()

        parsed = _parse_query(query)
        self.logger.info(f"Parsed : {parsed}")

        service_url = f"{HA_URL}/api/services/{parsed['domain']}/{parsed['action']}"
        payload = {"entity_id": parsed["entity_id"]}

        try:
            async with httpx.AsyncClient(timeout=HA_TIMEOUT) as client:
                response = await client.post(
                    service_url,
                    headers=self._headers,
                    json=payload
                )
                response.raise_for_status()

        except httpx.TimeoutException:
            return self._failure("Home Assistant timeout", latency_ms=self._elapsed_ms(start))
        except httpx.ConnectError:
            return self._failure(f"Home Assistant inaccessible : {HA_URL}", latency_ms=self._elapsed_ms(start))
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return self._failure("Token Home Assistant invalide", latency_ms=self._elapsed_ms(start))
            if e.response.status_code == 404:
                return self._failure(
                    f"Entité introuvable : {parsed['entity_id']}",
                    latency_ms=self._elapsed_ms(start)
                )
            return self._failure(
                f"Erreur HA HTTP {e.response.status_code}",
                latency_ms=self._elapsed_ms(start)
            )
        except Exception as e:
            return self._failure(f"Erreur inattendue HA : {str(e)}", latency_ms=self._elapsed_ms(start))

        latency = self._elapsed_ms(start)
        response_text = _build_response(parsed)
        self.logger.info(f"HA OK : {response_text} ({latency}ms)")

        return self._success(
            content=response_text,
            metadata={
                "entity_id": parsed["entity_id"],
                "action": parsed["action"],
                "domain": parsed["domain"],
                "room": parsed["room_label"],
                "ha_url": HA_URL,
            },
            latency_ms=latency
        )

    async def get_states(self) -> list:
        """Récupère toutes les entités HA disponibles"""
        try:
            async with httpx.AsyncClient(timeout=HA_TIMEOUT) as client:
                response = await client.get(
                    f"{HA_URL}/api/states",
                    headers=self._headers
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            self.logger.error(f"Erreur get_states : {e}")
            return []

    async def check_connection(self) -> bool:
        """Vérifie la connexion à Home Assistant"""
        if not HA_ENABLED or not HA_TOKEN:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{HA_URL}/api/",
                    headers=self._headers
                )
                return response.status_code == 200
        except Exception as e:
            self.logger.warning(f"HA check_connection failed : {e}")
            return False# (coller le contenu du fichier téléchargé ha_agent.py)
