# Dette structurelle de NéronOS

**Mise à jour : 3 septembre 2026**

Cette page reporte dans la documentation de référence la dette que seul le
dépôt documentait jusqu'ici. Elle conditionne l'ordre de travail
`Cœur → Architecte → SelfModel → Capabilities/MCP → WorldModel` : plusieurs
de ces points empêchent aujourd'hui de « finaliser le Cœur » proprement.

Toutes les valeurs ci-dessous sont **mesurées**, pas estimées.

## 1. Couplage circulaire parent ↔ sous-modules

Le dépôt parent et les sous-modules s'importent mutuellement :

```
server/core, server/goal, server/voice      ──importent──▶  modules.*, agents.*, tools.*
server/modules, server/agents, server/tools ──importent──▶  core.*, goal.*, llm.*
```

**303 sites d'import inter-plateformes**, formant **une seule composante
fortement connexe de 8 nœuds** (agents, core, goal, integrations, llm,
modules, tools, voice).

Conséquences : le Core ne peut pas être audité isolément, le parent ne peut
pas évoluer sans casser un sous-module, et les tests du parent sondent des
internes de sous-module.

Cible : `Parent ──▶ interfaces / contrats ──▶ sous-modules`.

## 2. Code métier hébergé par le parent

Environ **26 000 lignes** exécutées en production mais architecturalement
mal placées :

| Paquet du parent | Lignes | Destination |
|---|---|---|
| `server/modules` | ~12 000 | Core, Goal, SelfModel selon le paquet |
| `server/agents` | ~11 000 | Goal (l'usine) et Capabilities |
| `server/tools` | ~3 000 | Goal |

Rien ne doit être déplacé avant d'avoir traité le point 1 : déplacer du code
qui importe en cercle ne ferait que déplacer le problème.

## 3. Double nom de paquet pour `server/common`

`PYTHONPATH=/etc/neronOS:/etc/neronOS/server` rend le socle partagé
importable sous **deux noms** : `common.x` et `server.common.x`. Python
charge alors **deux modules distincts pour un même fichier**, donc deux jeux
d'état. C'est ce qui avait fait échouer l'enregistrement des métriques
Prometheus. À unifier sur un seul nom.

## 4. Watchdog inexistant

`server/watchdog` est un sous-module **vide** : `VERSION = v0.0.0`, aucun
code. Le nœud est déclaré dans `neron.server.yaml` (`127.0.1.6:8003`) mais
absent de `neron.target`.

**Le maillon « constate » de l'Architecte n'existe donc pas.**

Conséquence observée en production le 2 septembre 2026 : faute de Watchdog,
c'est **Doctor qui réparait** — il redémarrait tout service dont une sonde
HTTP échouait, toutes les 5 minutes, sans mémoire d'un cycle à l'autre. Core,
qui met ~25 s à démarrer et jusqu'à 90 s à s'arrêter, était redémarré avant
d'avoir pu répondre : il n'atteignait jamais l'état sain que le redémarrage
cherchait à rétablir. La machine est restée instable plusieurs heures.

Cela contredisait directement la règle *« Doctor analyse, Goal répare »* et
*« ne pas faire de Doctor un Goal »*.

**Corrigé le 3 septembre 2026** : le diagnostic périodique ne répare plus, il
constate et recommande (`diagnosed_not_repaired`). La correction reste
possible mais uniquement sur appel explicite de `POST /fixes`, bornée par un
délai de grâce (ne pas redémarrer un service qui démarre) et un cooldown (ne
pas redémarrer deux fois de suite le même service). Doctor tiendra ce rôle
provisoirement jusqu'à ce que Goal assume la réparation.

## 5. Unités systemd non versionnées

Règle en vigueur : toute unité déployée doit être versionnée dans
`system/deploy/systemd/`, et *« la documentation ne doit pas inventer de
services correspondant à d'anciennes architectures »*.

Deux unités déployées y échappaient : `ollama.service` et `llama.service`.

`llama.service` pointait vers `/etc/neron/llama/` — **racine abandonnée**,
inexistante depuis la migration vers `/etc/neronOS`. Elle a échoué et
redémarré **27 857 fois**, une fois toutes les 3 secondes, saturant CPU, RAM
et swap. Le binaire `llama-server` visé n'existe plus sur la machine, son
port (8081) ne correspondait pas à la configuration (`llama_cpp_host: 8080`),
et aucune tâche ne sélectionne le provider `llama_cpp`.

**Désactivée le 2 septembre 2026.** Ollama assure ce rôle
(`default_provider: ollama`, `safety_floor_provider: ollama`).

## 6. Tests neutralisés

Huit modules de `tests/` sondent des API de sous-module supprimées ou
renommées. Ils sont conservés mais désactivés par un `pytest.skip` de niveau
module, afin que la suite reste collectable :

`test_builder`, `test_dynamic_predicate_discovery`,
`test_goal_v2_provider_memory_api`, `test_identity_loader`,
`test_memory_ontology`, `test_oblivia_normalization`, `test_providers_a2a`,
`test_selfmodel_system_api`.

À noter : `core.modules.goal_v2`, que `test_goal_v2_provider_memory_api`
importe, **n'existe pas** — ce test ne collecte plus rien.

## 7. Découplage Core → Goal — état mesuré

Core importait les internes de Goal au lieu de passer par HTTP, ce qui
faisait tourner le code de Goal **dans le processus Core**, avec ses propres
singletons au-dessus du même stockage, sans verrou inter-processus.

| Étape | Imports Core → Goal |
|---|---|
| Constat initial | 26 |
| Après suppression du code mort | 22 |
| Après retrait des routers Goal montés par Core | **21** |

Core servait **28 routes appartenant à Goal** (`/goals/*`, `/projects/*`,
`/agents/*`). Elles ont été retirées : Core renvoie désormais 404 et
Goal:8030 est l'unique propriétaire de son API.

Les 21 dépendances restantes sont bloquées par : endpoints Goal manquants
(9), frontière synchrone/asynchrone du client HTTP (4), managers Goal passés
en objet à `CognitiveCore` (4), CRUD de plans (1), healthcheck par
importabilité (1), lecture de tâches (1), plans via le dispatcher (1).

## 8. Ce qui manque encore à la supervision

- **Doctor ne surveille pas Goal** : ses sondes ne couvrent que Core, LLM et
  Ollama. Une panne de Goal:8030 n'est détectée par rien.
- **`GET /openapi.json` de Goal renvoie 500** : le service répond
  correctement sur ses routes, mais son schéma OpenAPI est cassé.
- **Aucune route réseau vers Goal** : Caddy ne route que `/api/*` vers
  Core:8010. Aucun client web ne peut atteindre Goal directement.
