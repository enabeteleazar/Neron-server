# Homebox / Néron

## 🧠 Présentation

**Homebox / Néron** est une plateforme personnelle auto-hébergée destinée à centraliser, superviser et faire évoluer un ensemble de services techniques autour de trois piliers :

- 🏠 **Domotique & services locaux**
- 🧩 **Infrastructure Docker modulaire**
- 🤖 **Néron**, assistant intelligent orienté orchestration, supervision et sécurité

Le projet est conçu pour être **évolutif**, **sécurisé** et **maîtrisé**, avec une séparation claire entre environnements *dev* et *prod*.

---

## 🎯 Objectifs du projet

- Centraliser les services auto-hébergés
- Superviser l’infrastructure (conteneurs, réseau, système)
- Automatiser la maintenance et les sauvegardes
- Préparer une architecture orientée IA (Néron)
- Garantir la sécurité et la traçabilité des flux

---

## 🧱 Architecture générale


neron/
├── dev/
│   ├── neron/
│   └── services/
├── prod/
│   ├── neron/
│   └── services/
└── data/


 Principes clés
	•	services/ : code, docker-compose, configuration
	•	data/ : volumes persistants (non versionnés)
	•	dev / prod : environnements strictement séparés

---

## 🧩 Services principaux

Déjà intégrés
	*	Portainer
	*	Homeassistant
	*	Dashboars
	*	llama + telegram
	*	Prometheus
	*	cAdvisor

À venir
	•	Grafana
	•	Netdata
	•	Nginx Proxy Manager
	•	Uptime Kuma
	•	Services IA Néron

---

### 🤖 Néron (vision)

Néron est un projet d’assistant intelligent auto-hébergé, pensé comme :
	•	Un chef d’orchestre des services Homebox
	•	Un moteur de supervision augmentée
	•	Un futur auditeur de sécurité (analyse des flux, détection d’anomalies)

L’architecture vise à permettre :
	•	Une évolution modulaire
	•	Une future distribution (multi-nœuds)
	•	L’intégration progressive de modèles LLM locaux

---

### 🔐 Sécurité & bonnes pratiques
	•	Séparation code / données
	•	Variables sensibles via .env unique
	•	Pas d’accès distant exposé par défaut
	•	Préparation à l’audit réseau (Neron-SecurityAudit)

---

### 🗺️ Roadmap (extrait)

v1.x — Stabilisation & infrastructure
	•	v1.2.x : correctifs & normalisation
	•	v1.3.0 : monitoring (Prometheus + cAdvisor)
	•	v1.4.0 : proxy & monitoring réseau
	•	v1.5.0 : automatisation & maintenance
	•	v1.6.0 : orchestration des services
	•	v1.7.0 : accès distant sécurisé

v2.x — Néron
	•	Architecture cœur Néron
	•	Agents et modules
	•	Audit de sécurité assisté par IA
	•	Interactions système avancées

---

### 🚀 Déploiement

Chaque service dispose de son propre docker-compose.yaml.

Philosophie

Construire une infrastructure personnelle propre, compréhensible et évolutive,
avant d’y ajouter de l’intelligence.

⸻

### 📄 Licence

Projet personnel — usage privé / expérimental.
