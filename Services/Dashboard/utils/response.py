# backend/utils/response.py

from datetime import datetime
from typing import Any, Dict, Literal

StatusType = Literal[“ok”, “degraded”, “down”]

def now_iso() -> str:
“”“Retourne le timestamp actuel en ISO 8601”””
return datetime.utcnow().isoformat() + “Z”

def api_response(
status: StatusType,
data: Any = None,
error: str = None
) -> Dict[str, Any]:
“””
Format standardisé pour toutes les réponses API

```
Args:
    status: État du service ("ok", "degraded", "down")
    data: Données à retourner (dict, list, etc.)
    error: Message d'erreur optionnel

Returns:
    Dict avec structure standardisée
"""
response = {
    "status": status,
    "timestamp": now_iso()
}

if error:
    response["error"] = error

if data is not None:
    response["data"] = data

return response
```

def success_response(data: Any = None) -> Dict[str, Any]:
“”“Raccourci pour une réponse OK”””
return api_response(“ok”, data=data)

def degraded_response(data: Any = None, error: str = None) -> Dict[str, Any]:
“”“Raccourci pour une réponse dégradée”””
return api_response(“degraded”, data=data, error=error)

def error_response(error: str, data: Any = None) -> Dict[str, Any]:
“”“Raccourci pour une réponse en erreur”””
return api_response(“down”, data=data, error=error)
