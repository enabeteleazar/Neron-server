# NéronOS — Architecture de référence

> **Ce document n'est plus la référence architecturale.**
> La source de vérité est la documentation Notion (décision du 03/09/2026) :
> page **« Architecture de NéronOS »**, complétée par **« NéronOS — Roadmap
> Maître »**, **« État du projet NéronOS »** et **« Fiabilité NéronOS — Plan
> actuel »**.
>
> Le contenu qui vivait ici (les quatre blocs, la cartographie du dépôt, les
> contrats inter-plateformes, la dette structurelle) a été retiré pour qu'il
> ne subsiste **qu'une seule autorité**. Ce fichier ne reste que parce qu'une
> douzaine de renvois pointent vers lui ; il ne décrit plus l'architecture.

---

## Où trouver quoi

| Question | Où répondre |
|---|---|
| Quelle est l'architecture cible ? | Notion — *Architecture de NéronOS* (cinq plateformes, Cœur / Architecte / SelfModel / Capabilities) |
| Dans quel ordre travailler ? | Notion — *NéronOS — Roadmap Maître* |
| Qui répare quoi ? | Notion — *Watchdog — Architecture et rôle* : Watchdog constate → Doctor analyse → Goal répare |
| Où en est le découplage mesuré ? | [phase2a](phase2a-core-decoupling.md) · [2b](phase2b-kernel-extraction.md) · [2c](phase2c-core-goal-http-contract.md) · [2d](phase2d-goal-boundary-decision.md) · [2e](phase2e-core-goal-separation.md) |
| Quelle est la topologie réelle ? | `neron.server.yaml`, section `nodes` — seule source de vérité des ports |

Les documents `phase2*.md` restent dans le dépôt : ce sont des **mesures**
(comptages d'imports, contrats HTTP, décisions de frontière), pas une
architecture concurrente. Ils constatent l'état du code ; Notion dit la cible.

## Dette structurelle

Elle n'est plus décrite ici. Elle a été reportée dans Notion afin que la
documentation de référence porte aussi ce que le code impose — couplage
circulaire parent ↔ sous-modules, code métier hébergé par le parent, double
nom de paquet `server/common`, Watchdog inexistant.
