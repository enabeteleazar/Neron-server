# Architecture Cognitive de Néron

# Vision

Néron n’est pas un simple chatbot.

L’objectif est de construire un système cognitif autonome local capable de :

- s’observer ;
- comprendre son environnement ;
- définir des objectifs ;
- planifier ;
- agir ;
- se corriger ;
- évaluer ses résultats ;
- apprendre ;
- évoluer.

---

# État Actuel du Noyau Cognitif

| Module | État |
|---|---|
| SelfModel | ✅ |
| WorldModel | ✅ |
| Cognitive Loop | ✅ |
| Cognitive Daemon | ✅ |
| GoalSystem | 🔄 |
| Watchdog | 🔄 |
| SelfRepair | 🔄 |
| Critic | ⏳ |
| Planner | ⏳ |
| ActionExecutor | ⏳ |

---

# 1. SelfModel ✅

## Rôle

Le `SelfModel` représente l’état interne de Néron.

Il répond à :

```text
Qui suis-je ?
Dans quel état suis-je ?
```

## Fonctions actuelles

- surveillance CPU ;
- surveillance RAM ;
- surveillance disque ;
- état des services ;
- uptime lisible ;
- historique des intents ;
- historique des agents ;
- mémoire cognitive courte ;
- score de stabilité ;
- charge cognitive ;
- activité récente ;
- diagnostics ;
- recommandations ;
- état mental ;
- suivi boucle cognitive.

## Fonctionnement actuel

Le SelfModel génère maintenant un état cognitif complet :

```text
Néron est stable.
CPU 20%
RAM 42%
Boucle cognitive active.
Environnement stable.
```

## Capacités intégrées

### Mémoire cognitive

```text
- objectif actif
- dernière action
- dernière décision
- dernier raisonnement
- activité récente
```

### Mémoire système

```text
- services actifs
- agents disponibles
- état watchdog
- score stabilité
```

---

# 2. WorldModel ✅

## Rôle

Le `WorldModel` représente l’environnement externe de Néron.

Il répond à :

```text
Dans quel état est le monde autour de moi ?
```

## Fonctions actuelles

### Réseau

- interfaces réseau ;
- connectivité Internet ;
- DNS ;
- passerelle réseau.

### Services externes

- Home Assistant ;
- Ollama ;
- Néron Core API ;
- Néron LLM API.

### Machine hôte

- hostname ;
- load average ;
- uptime machine ;
- utilisateurs connectés.

## Architecture

Le WorldModel fonctionne via :

```text
neron-world-model-loop.service
```

avec mise à jour automatique périodique.

## État JSON persistant

```text
/etc/neron/data/world_model_state.json
```

## API disponibles

```text
/world-model/context
/world-model/status
/world-model/summary
```

## Intégration au SelfModel

Le SelfModel affiche maintenant :

```text
Monde externe :
- Environnement : stable
- Internet : accessible
- DNS : fonctionnel
- Home Assistant : actif
- Ollama : actif
- Néron LLM API : actif
- Néron Core API : actif
```

---

# 3. GoalSystem 🔄

## Rôle

Le `GoalSystem` gérera les objectifs internes.

Il répondra à :

```text
Que dois-je accomplir ?
```

## Fonctions prévues

- objectifs actifs ;
- priorités ;
- résolution d’objectifs ;
- persistance ;
- génération automatique d’objectifs ;
- suivi des tâches.

## Exemples

```text
Restaurer le service LLM
Réduire la charge CPU
Libérer de l’espace disque
Maintenir la stabilité système
```

---

# 4. Watchdog 🔄

## Rôle

Le `Watchdog` surveille les anomalies système.

## Fonctions prévues

- surveillance services ;
- surveillance ressources ;
- alertes ;
- détection erreurs ;
- timeout ;
- anomalies comportementales.

## Exemples

```text
neron-llm arrêté
CPU critique
RAM excessive
API indisponible
```

---

# 5. SelfRepair 🔄

## Rôle

Le `SelfRepair` proposera ou exécutera des corrections.

## Fonctions prévues

- redémarrage automatique ;
- propositions de réparation ;
- gestion du risque ;
- journalisation ;
- corrections supervisées.

## Exemple

```text
Proposition :
→ redémarrer neron-llm

Risque :
→ faible
```

---

# 6. Critic ⏳

## Rôle

Le `Critic` évaluera les décisions et actions.

## Fonctions prévues

- validation des résultats ;
- mesure succès/échec ;
- analyse qualité ;
- scoring décisionnel.

---

# 7. ActionExecutor ⏳

## Rôle

Le `ActionExecutor` exécutera les actions décidées.

## Fonctions prévues

- commandes système ;
- orchestration systemd ;
- appels API ;
- orchestration agents ;
- sécurité d’exécution.

---

# 8. Planner ⏳

## Rôle

Le `Planner` transformera les objectifs en plans d’action.

## Fonctions prévues

- découpage tâches ;
- orchestration multi-étapes ;
- priorisation ;
- adaptation dynamique.

## Exemple

```text
Objectif :
→ Restaurer neron-llm

Plan :
1. Vérifier le service
2. Lire les logs
3. Tenter un restart
4. Vérifier le healthcheck
5. Valider le retour du service
```

---

# Architecture Cognitive Cible

```text
SelfModel
    ↓
GoalSystem
    ↓
Planner
    ↓
ActionExecutor
    ↓
Critic
    ↓
Memory
```

En surveillance parallèle :

```text
WorldModel
Watchdog
SelfRepair
```

---

# Boucle Cognitive Globale

```text
SelfModel + WorldModel
        ↓
Watchdog détecte un problème
        ↓
GoalSystem crée un objectif
        ↓
Planner prépare un plan
        ↓
ActionExecutor exécute
        ↓
Critic évalue
        ↓
Memory apprend
```

---

# Vision Long Terme

Néron vise une architecture :

```text
locale
autonome
agentique
modulaire
évolutive
```

Inspirée des architectures cognitives modernes et des assistants autonomes avancés.
