# Neron — Interface Vocale Web

Interface vocale locale en HTML/CSS/JS + Express.
Pipeline : **Microphone → STT → LLM Core → TTS**

-----

## Prérequis

- Node.js >= 18
- OpenSSL (pour le certificat HTTPS)
- Services `neron_stt` et `neron_core` accessibles sur le réseau

-----

## Installation

```bash
git clone <repo>
cd neron_web_clean
npm install
```

-----

## Certificat HTTPS (obligatoire pour le micro sur réseau local)

```bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes -subj /CN=neron-local
```

### Installer le certificat sur iPhone/iPad

1. Copier le certificat dans le dossier public :
   
   ```bash
   cp cert.pem public/cert.pem
   ```
1. Depuis Safari sur l’iPhone, ouvrir `https://<ip>:8080/cert.pem`
1. **Réglages → Général → VPN et gestion des appareils → Installer**
1. **Réglages → Général → Informations → Réglages du certificat → Activer neron-local**

-----

## Lancement

```bash
NERON_CORE_URL=http://<ip>:8000 NERON_STT_URL=http://<ip>:8001 npm start
```

Le serveur démarre sur `https://localhost:8080`.  
Accessible depuis le réseau local sur `https://<ip>:8080`.

-----

## Architecture réseau

```
iPhone (Safari)
    |
    | HTTPS :8080
    v
Serveur Express (neron_web)
    |               |
    | HTTP :8001    | HTTP :8000
    v               v
neron_stt        neron_core
(Whisper)        (LLM Ollama)
```

Le serveur Express agit comme **proxy** entre le client HTTPS et les services HTTP internes, évitant les erreurs de mixed content.

-----

## Endpoints API

|Méthode|Route        |Description                        |
|-------|-------------|-----------------------------------|
|GET    |`/api/health`|Statut du serveur                  |
|GET    |`/api/config`|URLs actuelles STT et Core         |
|POST   |`/api/config`|Modifier les URLs STT et Core      |
|POST   |`/api/stt`   |Proxy multipart → STT `/transcribe`|
|POST   |`/api/core`  |Proxy JSON → Core `/input/text`    |

-----

## Format des services externes

### STT (`POST {STT_URL}/transcribe`)

```
Content-Type: multipart/form-data
Body: file=<blob audio>

Réponse: { "text": "transcription..." }
```

### Core LLM (`POST {CORE_URL}/input/text`)

```json
{ "text": "message utilisateur" }

Réponse: { "response": "réponse de Neron" }
```

-----

## Structure du projet

```
neron_web_clean/
├── public/
│   ├── index.html       - Interface principale
│   ├── css/
│   │   └── style.css    - Thème dark violet + animations
│   └── js/
│       └── app.js       - Pipeline vocal complet
├── server/
│   └── index.js         - Express + proxy STT/Core + HTTPS
├── cert.pem             - Certificat auto-signé (généré)
├── key.pem              - Clé privée (générée)
├── package.json
└── README.md
```

-----

## Changelog

### v1.0.0 — 2026-02-23

**Conversion Expo → Web**

- Suppression de toutes les dépendances Expo/React Native (~40 packages)
- Réécriture complète de l’interface en HTML/CSS/JS vanilla
- Réécriture du serveur Express en ES modules (suppression TypeScript)
- Une seule dépendance : `express`

**Réseau**

- Ajout du support HTTPS avec certificat auto-signé
- Ajout d’un proxy Express pour STT et Core (résolution du mixed content HTTPS→HTTP)
- Exposition du service `neron_stt` sur `Neron_Network` Docker
- Correction de la route STT : `/speech` → `/transcribe`
- Résolution du problème multipart : suppression de `express.json()` sur la route `/api/stt`

**Compatibilité**

- Réécriture de `app.js` en ES5 pour compatibilité Safari/iPhone
- Suppression des tirets typographiques et backticks problématiques
- Priorité au format `audio/mp4` pour l’enregistrement sur Safari iOS
- Timeout configurable (défaut : 60s)

**HTTPS / iOS**

- Génération du certificat via `openssl`
- Installation du profil sur iPhone via Safari
- Activation de la confiance certificat dans les réglages iOS
