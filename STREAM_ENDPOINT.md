# Endpoint `/input/stream` - Documentation

## Description

L'endpoint `/input/stream` permet de recevoir les réponses de Néron en **streaming**, utilisant le format **NDJSON** (newline-delimited JSON).

## Utilisation

### Requête
```bash
POST /input/stream HTTP/1.1
Content-Type: application/json

{
  "text": "Dis-moi bonjour",
  "mode": "default",
  "context": "optional context"
}
```

### Modes Supportés
- `default` - Réponse directe du LLM
- `plan` - Génère un plan détaillé
- `autopilot` - Mode autonome étendu
- `pipeline` - Routage Intent + LLM avec metadata

### Réponse (NDJSON Stream)

Le serveur retourne des lignes JSON séparées par des newlines:

```json
{"type": "metadata", "intent": "assistant", "confidence": 0.95}
{"type": "chunk", "data": "Bonjour! "}
{"type": "chunk", "data": "Comment ça "}
{"type": "chunk", "data": "va?"}
{"type": "complete", "success": true}
```

### Types de Réponse

| Type | Champs | Signification |
|------|--------|---------------|
| `metadata` | `intent`, `confidence` | Metadata (mode pipeline seulement) |
| `chunk` | `data` | Part dela réponse (streaming) |
| `complete` | `success` | Fin du stream |
| `error` | `message` | Erreur lors du traitement |

## Exemple Python

```python
import httpx
import json

async def stream_text(text: str, mode: str = "default"):
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            "http://localhost:8010/input/stream",
            json={"text": text, "mode": mode},
        ) as response:
            async for line in response.aiter_lines():
                if line.strip():
                    data = json.loads(line)
                    if data["type"] == "chunk":
                        print(data["data"], end="", flush=True)
                    elif data["type"] == "error":
                        print(f"\nError: {data['message']}")
```

## Headers

- `X-API-Key` (optionnel) - Clé API si authentification activée
- `Accept: application/x-ndjson` - Format de réponse

## Status Codes

- `200` - Stream démarré
- `403` - Clé API invalide
- `500` - Erreur serveur

## Avantages du Streaming

✅ Meilleure UX - affichage progressif des réponses
✅ Lower latency - pas d'attente de réponse complète
✅ Moins de mémoire - pas de buffering de la réponse entière
✅ Real-time - metadatas immédiatement disponibles
