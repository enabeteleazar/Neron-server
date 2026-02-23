# Changelog

Toutes les modifications notables de ce projet sont documentées ici.  
Format basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/).

-----

## [1.0.0] — 2026-02-23

### Ajouté

- Interface vocale web complète (HTML/CSS/JS vanilla)
- Serveur Express avec support HTTPS via certificat auto-signé
- Proxy Express pour les services STT et Core LLM (résolution mixed content)
- Route `/api/stt` — proxy multipart vers `neron_stt`
- Route `/api/core` — proxy JSON vers `neron_core`
- Route `/api/config` — lecture et mise à jour des URLs des services
- Route `/api/health` — statut du serveur
- Script `gen-cert` pour générer le certificat auto-signé
- Waveform animée pendant l’enregistrement
- Orbe animé avec 4 états : idle / listening / processing / speaking
- TTS via Web Speech Synthesis API (voix fr-FR)
- Timeout configurable sur les appels réseau (60s)
- Compatible Safari iOS (ES5, format audio mp4)

### Modifié

- Conversion complète depuis Expo/React Native vers web pur
- Réécriture du serveur `index.ts` (TypeScript) en `index.js` (ES modules)
- Route STT corrigée : `/speech` → `/transcribe`
- Exposition du service Docker `neron_stt` sur `Neron_Network`
- Port serveur : 5000 → 8080

### Supprimé

- Toutes les dépendances Expo/React Native (~40 packages)
- Metro bundler et pipeline de build mobile
- TypeScript, Drizzle ORM, React Query
- Landing page Expo Go
- Scripts de build iOS/Android

### Corrigé

- Mixed content HTTPS→HTTP via proxy serveur
- Problème multipart : suppression de `express.json()` sur `/api/stt`
- Compatibilité Safari : réécriture en ES5 sans backticks ni async/await
- Wildcard Express 5 : `*` → `/{*path}`
- Certificat auto-signé non approuvé sur iOS : installation du profil
- Port STT Docker non exposé : ajout de `Neron_Network` au service
