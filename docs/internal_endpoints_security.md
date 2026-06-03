# Securite des Endpoints Internes

Date: 2026-06-02

## Politique

Les endpoints d'orchestration interne sont proteges par l'en-tete `X-API-Key` quand `settings.API_KEY` est configure et different de `changez_moi`.

La dependance commune est `core.api.auth.verify_api_key`.

## Routers proteges

- `/planner/*`
- `/tasks/*`
- `/evolution/*`
- `/projects/*`
- `/agents` et `/agents/build`, car ils sont exposes par le router projects et touchent au runtime/agent builder.

## Endpoints publics conserves

- `/`
- `/health`
- `/status`
- `/docs`

Ces endpoints restent accessibles sans cle pour conserver la compatibilite d'exploitation locale.

## Compatibilite

Les formats JSON publics ne changent pas. Seule la couche d'acces ajoute des reponses standard FastAPI:

- `401 {"detail": "API Key manquante"}`
- `403 {"detail": "API Key invalide"}`

