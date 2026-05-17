# Architecture Cognitive de Néron

## Vision

Néron n’est pas conçu comme un simple chatbot.

L’objectif est de construire un système cognitif autonome local capable de :

- comprendre son propre état ;
- comprendre son environnement ;
- définir des objectifs ;
- surveiller son fonctionnement ;
- corriger ses problèmes ;
- planifier des actions ;
- évaluer ses résultats ;
- apprendre progressivement.

---

# Architecture Cognitive Centrale

## 1. SelfModel ✅

### Rôle

Le `SelfModel` représente la conscience interne de Néron.

Il répond à :

> Qui suis-je ?  
> Dans quel état suis-je ?

### Fonctions

- surveillance CPU / RAM / disque ;
- état des services ;
- historique des intents ;
- historique des agents ;
- mémoire cognitive courte ;
- score de stabilité ;
- charge cognitive ;
- diagnostics ;
- recommandations ;
- activité récente ;
- uptime ;
- état mental ;
- boucle cognitive.

### Exemple

```text
Néron est stable.
CPU 12%
RAM 41%
Boucle cognitive active.
```

### État actuel

✅ Fonctionnel

---

## 2. GoalSystem

### Rôle

Le `GoalSystem` gère les objectifs internes de Néron.

Il répond à :

> Que dois-je accomplir ?

### Fonctions

- création d’objectifs ;
- priorisation ;
- suivi d’état ;
- objectifs actifs ;
- résolution d’objectifs ;
- persistance des objectifs.

### Exemples d’objectifs

```text
Restaurer le service LLM
Réduire la charge CPU
Libérer de l’espace disque
Maintenir la stabilité système
```

### Priorités

```text
critical
high
medium
low
```

### États possibles

```text
active
resolved
failed
paused
```

---

## 3. WorldModel

### Rôle

Le `WorldModel` représente l’environnement externe de Néron.

Il répond à :

> Dans quel état est mon environnement ?

### Fonctions

- état réseau ;
- état Home Assistant ;
- disponibilité des API ;
- machines du cluster ;
- connectivité ;
- état des services externes ;
- température système ;
- ressources distribuées.

### Exemple

```text
Home Assistant indisponible
Cluster partiellement accessible
Connexion Internet stable
```

---

## 4. Watchdog

### Rôle

Le `Watchdog` surveille les anomalies.

Il répond à :

> Quelque chose dérive-t-il ou tombe-t-il en panne ?

### Fonctions

- détection d’erreurs ;
- surveillance continue ;
- alertes ;
- surveillance des services ;
- surveillance ressources ;
- surveillance timeout ;
- détection comportements anormaux.

### Exemples

```text
neron-llm inactif
CPU critique
RAM excessive
boucle cognitive arrêtée
```

---

## 5. SelfRepair

### Rôle

Le `SelfRepair` propose ou exécute des corrections automatiques.

Il répond à :

> Comment corriger le problème détecté ?

### Fonctions

- génération de réparations ;
- classification des risques ;
- redémarrage services ;
- ajustements automatiques ;
- corrections supervisées ;
- journalisation des réparations.

### Exemple

```text
Proposition :
→ redémarrer neron-llm

Risque :
→ faible
```

### Philosophie

Au début :

```text
proposer uniquement
```

Puis progressivement :

```text
corriger automatiquement
```

---

## 6. Critic

### Rôle

Le `Critic` évalue les résultats des actions et décisions.

Il répond à :

> Est-ce que l’action a réussi ?

### Fonctions

- validation résultats ;
- mesure succès / échec ;
- analyse performances ;
- détection mauvaises stratégies ;
- scoring qualité décisionnelle.

### Exemple

```text
Réparation réussie
Temps de réponse amélioré
Stabilité restaurée
```

---

## 7. ActionExecutor

### Rôle

Le `ActionExecutor` applique les actions décidées.

Il répond à :

> Comment exécuter concrètement l’action ?

### Fonctions

- exécution commandes ;
- gestion services systemd ;
- appels API ;
- orchestration agents ;
- exécution sécurisée ;
- contrôle permissions.

### Exemple

```bash
systemctl restart neron-llm
```

---

## 8. Planner

### Rôle

Le `Planner` transforme les objectifs en plans d’action.

Il répond à :

> Quelles étapes faut-il suivre ?

### Fonctions

- génération de plans ;
- découpage tâches ;
- orchestration multi-étapes ;
- priorisation actions ;
- adaptation dynamique.

### Exemple

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

# Chaîne Cognitive Cible

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

Avec en surveillance continue :

```text
WorldModel
Watchdog
SelfRepair
```

---

# Logique Globale

```text
SelfModel + WorldModel
        ↓
Watchdog détecte une anomalie
        ↓
GoalSystem crée un objectif
        ↓
Planner prépare un plan
        ↓
ActionExecutor applique l’action
        ↓
Critic vérifie le résultat
        ↓
Memory conserve l’expérience
```

---

# Objectif Final

Construire un système capable de :

- s’observer ;
- comprendre son environnement ;
- définir ses priorités ;
- planifier ;
- agir ;
- vérifier ses résultats ;
- apprendre ;
- s’améliorer.

---

# Vision Long Terme

Néron vise une architecture :

```text
agentique
autonome
locale
modulaire
évolutive
```

Inspirée de systèmes comme JARVIS, AutoGPT, Devin, OpenDevin et les architectures cognitives modernes, mais totalement maîtrisée et hébergée localement.
