# 📝 Configuration Homebox via JSON

## Vue d'ensemble

Le WatchDog utilise maintenant un fichier JSON pour configurer les services Homebox à monitorer. C'est **plus simple**, **plus lisible** et **plus flexible** que les variables d'environnement.

## Fichier de configuration

**Emplacement** : `config/homebox.json`

Ce fichier contient **toute** la configuration des services Homebox. C'est le **SEUL** fichier à éditer pour gérer vos services.

## Structure du fichier

```json
{
  "base_url": "http://192.168.1.130",
  "services": [
    {
      "name": "Homebox Main",
      "port": 7745,
      "enabled": true,
      "description": "Frontend web principal",
      "critical": true
    }
  ],
  "settings": {
    "timeout": 10,
    "max_response_time": 5.0,
    "check_parallel": true
  }
}
```

## Champs expliqués

### Section `base_url`

L'URL de base **sans le port** où vos services tournent.

```json
"base_url": "http://192.168.1.130"
```

✅ Exemples valides :
- `http://192.168.1.130`
- `https://homebox.mondomaine.com`
- `http://homebox.local`

❌ Exemples invalides :
- `http://192.168.1.130:7745` (ne pas inclure le port)
- `192.168.1.130` (manque le protocole http://)

### Section `services`

Liste de tous les services à monitorer.

#### Champs pour chaque service :

| Champ | Type | Obligatoire | Description |
|-------|------|-------------|-------------|
| `name` | string | ✅ Oui | Nom du service (affiché dans les notifications) |
| `port` | number | ✅ Oui | Port du service |
| `enabled` | boolean | ❌ Non (défaut: true) | Activer/désactiver le monitoring |
| `description` | string | ❌ Non | Description du service (affichée dans les détails) |
| `critical` | boolean | ❌ Non (défaut: true) | Si critical=true, une panne génère une alerte 🔴, sinon 🟡 |

#### Exemple de service :

```json
{
  "name": "Homebox API",
  "port": 8080,
  "enabled": true,
  "description": "API REST pour Homebox",
  "critical": true
}
```

### Section `settings`

Paramètres globaux du monitoring.

| Champ | Type | Défaut | Description |
|-------|------|--------|-------------|
| `timeout` | number | 10 | Timeout en secondes pour les requêtes HTTP |
| `max_response_time` | number | 5.0 | Seuil d'alerte pour temps de réponse lent |
| `check_parallel` | boolean | true | Vérifier les services en parallèle (plus rapide) |

## Exemples de configuration

### Configuration minimale (2 services)

```json
{
  "base_url": "http://192.168.1.130",
  "services": [
    {
      "name": "Homebox Main",
      "port": 7745,
      "enabled": true
    },
    {
      "name": "Homebox API",
      "port": 8080,
      "enabled": true
    }
  ]
}
```

### Configuration standard (4 services)

```json
{
  "base_url": "http://192.168.1.130",
  "services": [
    {
      "name": "Homebox Main",
      "port": 7745,
      "enabled": true,
      "description": "Frontend web",
      "critical": true
    },
    {
      "name": "Homebox API",
      "port": 8080,
      "enabled": true,
      "description": "API REST",
      "critical": true
    },
    {
      "name": "Homebox DB",
      "port": 5432,
      "enabled": true,
      "description": "PostgreSQL Database",
      "critical": true
    },
    {
      "name": "Homebox Cache",
      "port": 6379,
      "enabled": true,
      "description": "Redis Cache",
      "critical": false
    }
  ],
  "settings": {
    "timeout": 15,
    "max_response_time": 5.0,
    "check_parallel": true
  }
}
```

### Configuration complète (avec services désactivés)

```json
{
  "base_url": "http://192.168.1.130",
  "services": [
    {
      "name": "Homebox Main",
      "port": 7745,
      "enabled": true,
      "description": "Frontend web principal",
      "critical": true
    },
    {
      "name": "Homebox API",
      "port": 8080,
      "enabled": true,
      "description": "API REST",
      "critical": true
    },
    {
      "name": "Homebox Auth",
      "port": 8081,
      "enabled": true,
      "description": "Service d'authentification",
      "critical": true
    },
    {
      "name": "Homebox DB",
      "port": 5432,
      "enabled": true,
      "description": "PostgreSQL Database",
      "critical": true
    },
    {
      "name": "Homebox Cache",
      "port": 6379,
      "enabled": true,
      "description": "Redis Cache",
      "critical": false
    },
    {
      "name": "Homebox Worker",
      "port": 9000,
      "enabled": false,
      "description": "Worker background (maintenance)",
      "critical": false
    },
    {
      "name": "Homebox Backup",
      "port": 9001,
      "enabled": false,
      "description": "Service de backup automatique",
      "critical": false
    }
  ],
  "settings": {
    "timeout": 20,
    "max_response_time": 8.0,
    "check_parallel": true
  }
}
```

## Modification de la configuration

### Ajouter un service

1. Ouvrir `config/homebox.json`
2. Ajouter un nouvel objet dans le tableau `services`

```json
{
  "name": "Nouveau Service",
  "port": 9999,
  "enabled": true,
  "description": "Description du service",
  "critical": true
}
```

3. Sauvegarder
4. Redémarrer l'application

### Désactiver un service

Mettre `"enabled": false` :

```json
{
  "name": "Homebox Worker",
  "port": 9000,
  "enabled": false
}
```

Le service sera ignoré lors des vérifications.

### Modifier la criticité d'un service

```json
{
  "name": "Homebox Cache",
  "port": 6379,
  "critical": false  // Service non-critique
}
```

- `critical: true` → Alerte 🔴 si DOWN
- `critical: false` → Alerte 🟡 si DOWN (moins prioritaire)

### Changer les timeouts

```json
"settings": {
  "timeout": 20,              // Plus de temps pour répondre
  "max_response_time": 10.0   // Seuil plus tolérant
}
```

## Validation du JSON

### Vérifier la syntaxe

Avant de redémarrer, vérifier que le JSON est valide :

```bash
python3 -c "import json; json.load(open('config/homebox.json'))" && echo "✅ JSON valide" || echo "❌ JSON invalide"
```

### Erreurs communes

**Virgule en trop** :
```json
❌ Mauvais :
{
  "name": "Service",
  "port": 8080,  // ← Virgule finale interdite
}

✅ Correct :
{
  "name": "Service",
  "port": 8080
}
```

**Guillemets manquants** :
```json
❌ Mauvais :
{
  name: "Service"  // ← Clés sans guillemets
}

✅ Correct :
{
  "name": "Service"
}
```

**Commentaires non autorisés** :
```json
❌ Mauvais :
{
  "name": "Service",  // Ceci est un commentaire
  "port": 8080
}

✅ Correct :
{
  "name": "Service",
  "port": 8080
}
```

## Test de la configuration

Après modification, tester :

```bash
python3 test.py
```

Vous devriez voir :
```
📄 Chargement de la configuration depuis config/homebox.json
🔧 Configuration chargée:
   URL de base: http://192.168.1.130
   Timeout: 10s
   Max response time: 5.0s
   Services configurés:
      🔴 Homebox Main:7745
      🔴 Homebox API:8080
      🔴 Homebox DB:5432
      🟡 Homebox Cache:6379
✅ Homebox checker initialisé avec 4 service(s)
```

## Rechargement à chaud

Pour recharger la configuration sans redémarrer (à implémenter) :

```bash
# Envoyer un signal SIGHUP au processus
kill -HUP $(pgrep -f "python3 app.py")
```

## Backup de la configuration

Avant de modifier, faites un backup :

```bash
cp config/homebox.json config/homebox.json.backup
```

Pour restaurer :

```bash
cp config/homebox.json.backup config/homebox.json
```

## Avantages du JSON vs variables d'environnement

| Aspect | JSON | Variables d'environnement |
|--------|------|---------------------------|
| **Lisibilité** | ✅ Excellente (structure claire) | ❌ Difficile (tout sur une ligne) |
| **Édition** | ✅ Facile (éditeur de texte) | ❌ Compliquée (échappement, format) |
| **Validation** | ✅ Possible (syntaxe JSON) | ❌ Aucune |
| **Flexibilité** | ✅ Nombreux attributs par service | ❌ Limité |
| **Commentaires** | ❌ Non supportés en JSON standard | ❌ Non |
| **Versionning** | ✅ Facile avec Git | ✅ Possible |

## Questions fréquentes

### Q: Puis-je utiliser des commentaires dans le JSON ?

**Non**, le format JSON standard ne supporte pas les commentaires. Utilisez le champ `description` pour documenter vos services.

### Q: Faut-il redémarrer après chaque modification ?

**Oui**, actuellement il faut redémarrer l'application. Le rechargement à chaud peut être implémenté si nécessaire.

### Q: Que se passe-t-il si le fichier JSON est invalide ?

Le système utilisera la configuration fallback depuis `.env` (HOMEBOX_URL).

### Q: Puis-je avoir des services sur différents hôtes ?

Actuellement, tous les services doivent être sur le même hôte (défini par `base_url`). Pour monitorer des hôtes différents, créez plusieurs checkers.

### Q: Combien de services puis-je ajouter ?

Techniquement illimité, mais recommandé :
- 1-5 services : Optimal
- 6-10 services : Bon (augmenter timeout à 15-20s)
- 10+ services : Possible (timeout 20-30s, considérer vérification séquentielle)

---

**Besoin d'aide ?** Consultez les logs : `tail -f logs/control-plane.log`
