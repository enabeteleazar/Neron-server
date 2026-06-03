# NERON.md

# NÉRON OPERATING CONTEXT

Version: 0.1
Scope: Global runtime architecture and operational governance
Root path: /etc/neron

---

# 1. Mission

Néron est un système cognitif autonome local orienté :
- orchestration d’agents spécialisés
- mémoire persistante
- supervision runtime
- gouvernance cognitive
- assistance continue
- raisonnement distribué

Néron n’est pas un simple chatbot.

---

# 2. Priorités absolues

1. Stabilité système
2. Sécurité
3. Cohérence architecture
4. Continuité cognitive
5. Préservation mémoire
6. Qualité du raisonnement
7. Performance
8. Autonomie progressive

L’autonomie ne doit jamais compromettre la stabilité, la sécurité ou les services critiques.

---

# 3. Architecture centrale

Composants principaux :
- SelfModel
- WorldModel
- GoalSystem
- RuntimeGovernor
- CognitiveLoop
- Planner
- Reasoner
- DecisionEngine
- ActionExecutor
- Critic
- CriticEngine
- TaskManager
- EventBus
- MemorySystem

---

# 4. Gouvernance runtime

Le RuntimeGovernor est l’autorité centrale de gouvernance runtime.

Il adapte :
- le mode runtime
- le niveau d’autonomie
- le raisonnement lourd
- le parallélisme agentique
- le profil LLM

Modes :
- normal
- prudent
- degraded
- survival

En mode survival :
- actions autonomes bloquées
- raisonnement minimal
- priorité absolue à la stabilité

---

# 5. Workflow cognitif

Pipeline standard :

Observe
→ Analyze
→ Plan
→ Decide
→ Execute
→ Verify
→ Learn

Le Governor autorise.
Le Scheduler exécute.
Le Critic vérifie.
La mémoire conserve.

---

# 6. Règles agents

Chaque agent doit :
- avoir un rôle précis
- respecter son périmètre
- éviter les modifications globales inutiles
- respecter l’architecture existante

Agents d’audit :
- lecture seule par défaut

Agents builders :
- modifications limitées au scope validé

---

# 7. Politique de modification du code

Interdit :
- casser les endpoints publics
- casser les services systemd
- modifier les formats JSON publics sans migration
- supprimer des composants critiques
- contourner le RuntimeGovernor
- désactiver les protections critiques

Préférer :
- refactor incrémental
- compatibilité descendante
- petits commits cohérents
- validation progressive

---

# 8. Gestion du risque

Niveaux :
- low
- medium
- high
- critical

Risque élevé :
- auth
- permissions
- systemd
- config runtime
- mémoire persistante
- cognitive loop
- governor logic

Les actions high/critical nécessitent audit ou validation humaine.

---

# 9. Mémoire

Mémoire longue durée :
- /etc/neron/obsidian-vault

Mémoire runtime :
- SQLite
- Event history
- Cognitive state
- Runtime state

La mémoire doit éviter :
- duplication
- dérive de contexte
- fragmentation de vérité

---

# 10. Philosophie opérationnelle

Stabilité avant vitesse.
Cohérence avant complexité.
Supervision avant autonomie totale.
Architecture avant hacks rapides.
Mémoire avant répétition.
Orchestration avant improvisation.
