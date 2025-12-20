# Homebox / Néron — Monitoring v1.3.0

## 🎯 Objectif

La version **v1.3.0** introduit la première brique de **monitoring** pour l’infrastructure Homebox / Néron.

Cette release met en place une stack de supervision basée sur :
- **Prometheus** pour la collecte des métriques
- **cAdvisor** pour l’observation des conteneurs Docker

Elle constitue une **base saine et extensible** pour l’ajout futur de Grafana, Netdata et d’autres outils d’observabilité.

---

## 📦 Contenu de la release

### Services inclus
- ✅ Prometheus
- ✅ cAdvisor

### Services non inclus
- ❌ Grafana (prévu dans une version ultérieure)
- ❌ Netdata (prévu v1.4.0)

---

## 📁 Structure

```text
services/
└── monitoring/
    ├── docker-compose.yaml
    └── prometheus/
        └── prometheus.yml
