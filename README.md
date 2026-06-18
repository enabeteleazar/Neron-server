Néron Core

Néron Core est le noyau cognitif du système Néron.

Il fournit les capacités fondamentales nécessaires au fonctionnement de Néron et constitue la base sur laquelle s’appuient les autres composants du système.

Mission

Néron Core est responsable de :

* l’identité du système
* l’orchestration cognitive
* la mémoire fondamentale
* le routage des intentions
* la supervision runtime
* les capacités cognitives essentielles

Néron Core n’est pas un assistant conversationnel.

Il constitue le moteur central d’un système d’exploitation personnel piloté par l’IA.

⸻

Architecture

Identity
Timer
Status
Memory
        ↓
Orchestrator
        ↓
Runtime

Les modules présents dans le Core doivent toujours être disponibles.

Ils ne peuvent pas être désactivés.

⸻

Modules cognitifs

Identity

Répond à la question :

Qui suis-je ?

Source de vérité :

NERON.md

⸻

Timer

Répond à la question :

Quand sommes-nous ?

Fonctions :

* date
* heure
* temps

⸻

Status

Répond à la question :

Dans quel état suis-je ?

Fonctions :

* état opérationnel
* état du Core
* état runtime

⸻

Memory

Répond à la question :

Que sais-je ?

Fonctions :

* mémorisation
* rappel
* stockage persistant

Backend :

SQLite

⸻

Principes

Le Core doit rester :

* simple
* stable
* prévisible
* indépendant

Toute fonctionnalité non essentielle doit être développée hors du Core.

⸻

Dépôts associés

neronOS
└── utilise
    └── neron_core
neron_core
├── Identity
├── Timer
├── Status
└── Memory

⸻

Version

Version actuelle :

0.2.0

⸻

Philosophie

Le Core doit pouvoir répondre aux questions fondamentales :

Qui suis-je ?
Quand sommes-nous ?
Dans quel état suis-je ?
Que sais-je ?

Les capacités avancées sont construites au-dessus de ces fondations.
