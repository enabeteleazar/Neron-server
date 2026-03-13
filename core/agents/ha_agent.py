# agents/ha_agent.py
# Neron Core - Agent Home Assistant (REST API directe)

import asyncio
import httpx
import unicodedata
from agents.base_agent import BaseAgent, AgentResult
from config import settings

HA_URL              = getattr(settings, "HA_URL", "http://homeassistant.local:8123")
HA_TOKEN            = getattr(settings, "HA_TOKEN", "")
HA_ENABLED          = getattr(settings, "HA_ENABLED", False)
HA_TIMEOUT          = 10.0
HA_REFRESH_INTERVAL = int(getattr(settings, "HA_REFRESH_INTERVAL", 5))  # minutes

# --- Mapping actions ---
TURN_ON_KEYS  = ["allume", "active", "ouvre", "demarre", "mets"]
TURN_OFF_KEYS = ["eteins", "desactive", "ferme", "arrete", "coupe"]

# Domaines HA par mots-clés
DOMAIN_KEYWORDS = {
    "light":               ["lumiere", "lampe", "plafonnier", "led", "spot", "ampoule"],
    "cover":               ["volet", "store", "rideau", "portail"],
    "climate":             ["thermostat", "chauffage", "climatiseur", "clim"],
    "switch":              ["prise", "interrupteur"],
    "fan":                 ["ventilateur", "vmc"],
    "alarm_control_panel": ["alarme"],
    "scene":               ["scene"],
}


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower().strip())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _detect_domain(query_norm: str) -> str | None:
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw in query_norm:
                return domain
    return None


def _score_entity(query_norm: str, entity: dict) -> int:
    score = 0
    entity_id = _normalize(entity.get("entity_id", ""))
    friendly  = _normalize(entity.get("attributes", {}).get("friendly_name", ""))

    for word in query_norm.split():
        if len(word) < 3:
            continue
        if word in entity_id:
            score += 2
        elif word in friendly:
            score += 1
        if any(word in part for part in entity_id.split(".")):
            score += 1

    return score


def _parse_query(query: str, ha_states: list) -> dict:
    q = _normalize(query)

    action = "turn_on"
    for k in TURN_OFF_KEYS:
        if k in q:
            action = "turn_off"
            break

    detected_domain = _detect_domain(q)

    candidates = ha_states
    if detected_domain:
        filtered = [
            e for e in ha_states
            if e.get("entity_id", "").startswith(detected_domain + ".")
        ]
        candidates = filtered if filtered else ha_states

    scored = [
        (entity, _score_entity(q, entity))
        for entity in candidates
    ]
    scored = [(e, s) for e, s in scored if s > 0]
    scored.sort(key=lambda x: x[1], reverse=True)

    if scored:
        best_entity = scored[0][0]
        entity_id   = best_entity["entity_id"]
        domain      = entity_id.split(".")[0]
        friendly    = best_entity.get("attributes", {}).get("friendly_name", entity_id)
        matched     = True
    else:
        domain    = detected_domain or "light"
        entity_id = f"{domain}.inconnu"
        friendly  = entity_id
        matched   = False

    return {
        "action":    action,
        "domain":    domain,
        "entity_id": entity_id,
        "friendly":  friendly,
        "matched":   matched,
    }


def _build_response(parsed: dict) -> str:
    action_label = "allumé" if parsed["action"] == "turn_on" else "éteint"

    if parsed["domain"] == "cover":
        action_label = "ouvert" if parsed["action"] == "turn_on" else "fermé"
    elif parsed["domain"] == "climate":
        action_label = "activé" if parsed["action"] == "turn_on" else "désactivé"

    friendly = parsed["friendly"].rstrip(".")
    return f"J'ai {action_label} {friendly}."


class HAAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="ha_agent")
        self._headers = {
            "Authorization": f"Bearer {HA_TOKEN}",
            "Content-Type": "application/json",
        }
        self._ha_states: list = []
        self._refresh_task: asyncio.Task | None = None

    async def on_start(self):
        if not HA_ENABLED or not HA_TOKEN:
            self.logger.warning("HA désactivé ou token manquant — states non chargés")
            return

        self._ha_states = await self.get_states()
        self.logger.info(f"HA states chargés : {len(self._ha_states)} entités")

        self._refresh_task = asyncio.create_task(self._refresh_loop())
        self.logger.info(f"HA refresh loop démarrée — intervalle : {HA_REFRESH_INTERVAL} min")

    async def on_stop(self):
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
            self.logger.info("HA refresh loop arrêtée")

    async def _refresh_loop(self):
        while True:
            await asyncio.sleep(HA_REFRESH_INTERVAL * 60)
            await self.reload()

    async def reload(self) -> int:
        self.logger.info("HA reload — rechargement des entités...")
        states = await self.get_states()
        if states:
            self._ha_states = states
            self.logger.info(f"HA reload OK — {len(self._ha_states)} entités")
        else:
            self.logger.warning("HA reload — aucune entité récupérée, cache conservé")
        return len(self._ha_states)

    async def execute(self, query: str, **kwargs) -> AgentResult:
        if not HA_ENABLED:
            return self._failure("Home Assistant non activé — configurez : make ha-agent")

        if not HA_TOKEN:
            return self._failure("Token Home Assistant manquant dans neron.yaml")

        self.logger.info(f"HA action pour : {repr(query)}")
        start = self._timer()

        if not self._ha_states:
            self.logger.warning("Cache HA vide — tentative de rechargement")
            self._ha_states = await self.get_states()

        parsed = _parse_query(query, self._ha_states)
        self.logger.info(f"Parsed : {parsed}")

        if not parsed["matched"]:
            return self._failure(
                f"Aucune entité HA trouvée pour : '{query}'",
                latency_ms=self._elapsed_ms(start)
            )

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
                "friendly":  parsed["friendly"],
                "action":    parsed["action"],
                "domain":    parsed["domain"],
                "ha_url":    HA_URL,
            },
            latency_ms=latency
        )

    async def get_states(self) -> list:
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
            return False
