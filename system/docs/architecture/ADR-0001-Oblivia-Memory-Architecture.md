# Oblivia — Architecture de la mémoire de Néron

Version : 1.0
Statut : Référence d'architecture

---

# 1. Vision

Oblivia est la mémoire de Néron.

Elle constitue l'unique source de vérité concernant les connaissances de Néron.

Aucun autre composant ne possède sa propre mémoire cognitive.

---

# 2. Principes fondateurs

## Source de vérité unique

Toute connaissance persistante appartient à Oblivia.

Core, Goal, SelfModel et les Agents consultent Oblivia.

Ils ne maintiennent jamais une mémoire parallèle.

---

## Séparation des responsabilités

Core

- détecte les intentions
- choisit le Provider
- route via A2A

Provider Registry

- sélectionne le Provider Memory

A2A

- transporte les requêtes

Oblivia

- comprend
- extrait
- stocke
- recherche
- rappelle
- oublie
- corrige

---

## Aucune logique mémoire dans Core

Le Core ne possède :

- aucune base mémoire
- aucune logique de stockage
- aucune logique de rappel

Il reste un routeur.

---

# 3. Modèle de connaissance

Une connaissance est représentée sous forme de relation.

Sujet
↓

Prédicat
↓

Objet

Exemple

user
↓

works_at
↓

Constructel

---

# 4. Entités

Une entité représente un objet du monde.

Exemples

- utilisateur
- personne
- entreprise
- ville
- animal
- projet
- document

---

# 5. Relations

Les relations décrivent les liens entre les entités.

Exemples

name

works_at

lives_at

likes

has_child

has_pet

spouse

project

---

# 6. Ontologie

Chaque relation possède une définition officielle.

Une relation décrit :

- son nom
- sa cardinalité
- sa catégorie
- son cycle de vie
- sa relation inverse éventuelle

Exemple

works_at

cardinality : one

category : work

lifecycle : replace

---

likes

cardinality : many

category : preference

lifecycle : preference

---

has_child

cardinality : many

category : family

lifecycle : accumulate

---

# 7. Cardinalité

Une relation possède une cardinalité.

one

Une seule valeur est actuelle.

many

Plusieurs valeurs peuvent coexister.

---

# 8. Temporalité

Certaines relations possèdent un historique.

La mémoire ne détruit pas une information.

Elle distingue :

- actuelle
- ancienne
- future (éventuellement)

Le stockage générique porte `valid_from`, `valid_to`, `is_current`,
`retracted`, `retracted_at`, `retraction_reason`, `lifecycle` et les conflits.
Le cycle de vie est résolu dans `server/memory/oblivia/ontology.py`, jamais
codé par prédicat dans l’adaptateur SQLite.

Cycles supportés :

- immutable ;
- replace ;
- accumulate ;
- preference ;
- event (déclaré seulement, sans prédicat actif).

`name`, `lives_at`, `works_at` et `spouse` utilisent `replace`. `likes`
utilise `preference`. `has_child` et `relation_to_user` utilisent
`accumulate`.

Le Memory Reasoner déterministe agrège les faits actifs reliés à `user` pour
les questions personnelles. Il sépare actuel, ancien et historique, filtre
rétractations et conflits, et n’utilise ni LLM ni souvenirs projet pour
produire une synthèse utilisateur.

Exemple

user

lives_at

Saron-sur-Aube

current=true

↓

user

lives_at

Troyes

current=true

↓

Saron-sur-Aube

current=false

---

# 9. Collections

Une phrase peut produire plusieurs relations.

Exemple

J'ai trois enfants :

Lounna

Ninna

Matthyas

↓

user

has_child

Lounna

↓

user

has_child

Ninna

↓

user

has_child

Matthyas

---

# 10. Idempotence

Une information identique ne doit jamais créer de doublon.

Dire deux fois

J'habite à Troyes

ne produit qu'un seul fait courant.

---

# 11. Historique

La mémoire conserve l'évolution.

Elle peut répondre :

Où j'habite ?

Où j'habitais avant ?

Où ai-je vécu ?

---

# 12. Recherche

Oblivia doit être capable de retrouver :

une entité

une relation

une collection

une information historique

une information actuelle

---

# 13. Rappel

Les réponses doivent être naturelles.

Jamais les triplets.

Exemple

Question

Comment s'appelle ma femme ?

Réponse

Ta femme s'appelle Alice.

---

# 14. Évolution

Les futures phases ajouteront :

- raisonnement
- graphe de connaissances
- embeddings
- mémoire épisodique
- mémoire procédurale
- mémoire autobiographique
- résolution de contradictions
- confiance
- provenance
- oubli contrôlé

---

# 15. Invariants

Toujours respecter :

✓ Core est un routeur

✓ A2A est le protocole

✓ Oblivia est l'unique mémoire

✓ Toute connaissance est structurée

✓ Les réponses passent par Oblivia

✓ Aucun stockage mémoire parallèle

✓ Les évolutions doivent préserver ces principes.
