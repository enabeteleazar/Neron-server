[33mcommit a544826fbacc7e8d2d5112f01bc967f3c9e8f035[m[33m ([m[1;36mHEAD[m[33m -> [m[1;32mdevelop[m[33m, [m[1;31morigin/develop[m[33m)[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 22 21:31:57 2026 +0000

    update .gitignore

[33mcommit 9ced2443a38761484d40200e0f9ad10f6c16e17c[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 22 21:19:54 2026 +0000

     Ajout de phrase descriptif des agents

[33mcommit 79963a8a5f1532c31739a8311094f92388118570[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 22 21:19:24 2026 +0000

     Ajout de phrase descriptif des agents

[33mcommit 88eb2ecbabceea64451ec50f6bd5dfc05db05e16[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 22 21:09:21 2026 +0000

     Ajout de phrase descriptif des modules

[33mcommit 7cf88f418cc4eaee94be65793d8538455ec399c0[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 22 13:47:49 2026 +0000

    chore: ajout modules ...

[33mcommit ec71594726387b06ba28662065eba3a361c66d78[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 22 10:05:45 2026 +0000

    feat: /status Telegram — score santé + prochaines tâches scheduler

[33mcommit d47f98dd64887b2ec0d527158d237618b09eaaa1[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 22 09:56:56 2026 +0000

    feat: /run et /workspace — exécution fichiers générés depuis Telegram

[33mcommit f999b293911631d98fca81a85144857e208176b7[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 22 09:40:34 2026 +0000

    feat: Scheduler APScheduler — auto-review 3h, rapport 8h, nettoyage hebdo

[33mcommit a512492207176e2c031576c9fc734e828d6ceeec[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 22 08:58:19 2026 +0000

    feat: Gateway WebSocket :18789 + Skills system + SessionStore intégrés

[33mcommit 2af1ab66716919baa2ed976227c44e3a810ea3cd[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 22 00:05:22 2026 +0000

    feat: Twilio — appel vocal sur demande via /call Telegram

[33mcommit e3d90e275d71af59ea4fd645104895b8e6261c0a[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 21 23:22:39 2026 +0000

    chore: nettoyage — suppression client web, migration Telegram comme canal unique

[33mcommit fcb9f250d49007bb7c7c8a52de88585b76c5fdc3[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 21 23:20:56 2026 +0000

    feat: routing telegram — input/stream pour LLM, input/text pour CodeAgent

[33mcommit 4101d7945337af01c1cabb2bb5057c38474772be[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 21 18:17:38 2026 +0000

    fix: strip markdown backticks from LLM code output before syntax check

[33mcommit 7475b465f803f363b62f7517bd45b382ff2d556b[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 21 18:07:09 2026 +0000

    feat: CodeAgent écrit les fichiers générés + fix intent TIME_QUERY trop agressif

[33mcommit 4509c19b8fa028e99d8e336be930cb4a320f0b7e[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 21 16:56:39 2026 +0000

    feat: CodeAgent autonome — génération/analyse/amélioration de code via Phi3

[33mcommit cbe8ad77acc4e820d3aa839faa5bc0082d144389[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Mar 20 12:52:16 2026 +0000

    fix(makefile): correction commande Python multiligne dans make ollama
    
    - Remplacement du bloc Python multiligne par une ligne unique
    - Corrige l'IndentationError qui empêchait la mise à jour de neron.yaml

[33mcommit 74df3acb61235f0fcd32d28240bee163d234665e[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Mar 19 07:55:20 2026 +0000

    chore: nettoyage neron.yaml.example — suppression tokens sensibles + version 2.2.0

[33mcommit 8bda95c55983293a45dfa5749e53aa07f45f4ca3[m
Merge: 27686c5 44f46bb
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Mar 19 07:53:03 2026 +0000

    Merge branch 'feature/personna' into develop

[33mcommit 44f46bbeb20c1b705698788907699d673eae2601[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Mar 19 07:52:17 2026 +0000

    fix(personality): suppression doublon personality/personality/ + exclusion DB
    
    - Suppression du dossier core/personality/personality/ (copie imbriquée parasite)
    - Suppression de persona_state.db du tracking git
    - Ajout .gitignore pour exclure persona_state.db (généré au runtime)

[33mcommit a483f83d2b9dddf89ee4faf8b0ff6cb7169c08a2[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Mar 19 07:50:01 2026 +0000

    feat(personality): intégration module persona v7
    
    - Ajout module core/personality/ (v7)
      - Personnalité persistante via SQLite
      - Traits, mood, energy_level, verbosity adaptatifs
      - Protection core_identity immuable
      - Historique des changements d'état
      - Validation ALLOWED_VALUES (str + booléens stricts)
    
    - llm_agent.py : system prompt dynamique via build_system_prompt()
      - Migration /api/generate → /api/chat (format messages)
      - Fallback transparent sur SYSTEM_PROMPT statique si module absent
    
    - intent_router.py : nouvel intent PERSONALITY_FEEDBACK
      - Feedbacks comportementaux interceptés avant le LLM
      - Mots-clés synchronisés avec INTENT_MATRIX du module
    
    - app.py : version 2.2.0
      - Handler _handle_personality_feedback()
      - Routes GET /personality/state
      - Routes GET /personality/history
      - Routes POST /personality/reset

[33mcommit 27686c5b3ba42ef23d30722c06d6cebd55643d2c[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Mar 16 18:46:05 2026 +0000

    Correction du code suite a erreur

[33mcommit 8269325ca2df6eac4b7a5ccbdb800f494f7b65d8[m
Merge: 9a773a2 1df1876
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Mar 16 08:01:09 2026 +0000

    Merge branch 'feature/install' into develop

[33mcommit 1df1876827791d0a1750d147866fb3638b5245aa[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Mar 16 07:57:27 2026 +0000

    fix(install): nettoyage .env + messages make install

[33mcommit 3196480d94e7d6562b467d77aae6da9b487c27ac[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Mar 16 07:44:42 2026 +0000

    fix(install): suppression .env + neron.service dynamique
    
    - Makefile: suppression dépendance .env dans make install
    - neron.service: placeholders __NERON_DIR__ et __NERON_USER__
    - Logs vers data/logs/, PYTHONPATH dynamique

[33mcommit 39da9ca4165b117fd856d53d4cb41d0aa0ec3eb1[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Mar 16 07:30:16 2026 +0000

    feat(install): structure /etc/neron/{server,client,data} + client web
    
    - install.sh: nouvelle structure /etc/neron/server|client|data
    - install.sh: étape 7/8 clone Neron_UI + service neron-client
    - install.sh: 8 étapes numérotées
    - Makefile: BASE_DIR dynamique via dirname

[33mcommit 9a773a238eb973ca9b2bfa68237bacb28aee4b46[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Mar 16 07:15:45 2026 +0000

    fix(db): correction schema table events
    
    - memory_agent.py: colonnes type, service, message ajoutées
    - Corrige l'erreur watchdog 'table events has no column named type'

[33mcommit fbe6353aa89ada19504a7f7484ba5ef3b50ead45[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 15 21:41:27 2026 +0000

    feat(tts): migration espeak+ffmpeg MP3 + déplacement neron_tts dans core
    
    - neron_tts/engine.py: espeak + conversion MP3 via ffmpeg (compat Safari iOS)
    - tts_agent.py: gestion tuple (bytes, mimetype) + path corrigé
    - app.py: mimetype dynamique audio/mpeg ou audio/wav
    - neron_tts déplacé dans core/ (plus propre)

[33mcommit b9ae47fbfb8459f769715e2651f381c88d617854[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 15 14:19:58 2026 +0000

    fix(voice): encode headers ASCII pour caractères spéciaux
    
    - app.py: encode X-Transcription et X-Response-Text en ASCII
    - Corrige erreur latin-1 sur caractères Unicode (tirets, accents)

[33mcommit 06eca503b511e44f4d5007878af05bc6471cb201[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 15 12:20:14 2026 +0000

    feat(tts): activation TTS espeak direct
    
    - neron_tts/engine.py: moteur espeak direct (bypass pyttsx3)
    - tts_agent.py: correction path neron_tts (3 niveaux)
    - app.py: réactivation tts_load_engine() et TTSAgent
    - Pipeline vocal complet : STT → LLM → TTS opérationnel

[33mcommit f6e50a1b5317ad2de7218d751d77975cadee95c6[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 14 23:03:12 2026 +0000

    fix(cors): ajout middleware CORS pour connexion client web
    
    - app.py: CORSMiddleware allow_origins=* pour autoriser le client web

[33mcommit 8c2e3a16dc7944ee06000cb924d84a743cb24eee[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 14 22:29:22 2026 +0000

    feat(client): make client — serveur HTTP port 8080
    
    - Makefile: cible make client pour servir le client web
    - Vérifie la présence de config.js, crée depuis l'exemple si absent
    - Affiche l'URL locale au démarrage

[33mcommit 3a302f0f46f6cec72abb2de20e789c88d651b26b[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 14 17:29:59 2026 +0000

    feat(ollama): recommandations hardware-aware via llmfit
    
    - scripts/llmfit/llmfit.py: détection hardware + scoring modèles LLM
    - scripts/llmfit/hf_models.json: base de données modèles HuggingFace
    - scripts/ollama_recommend.py: helper make ollama — affiche nom + score
    - Makefile: make ollama intègre llmfit avant sélection du modèle

[33mcommit f5b34fd610cca0a21309505598a2c4c5c50e5b45[m
Merge: 0131d11 31dc31e
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Mar 13 08:15:06 2026 +0000

    Merge branch 'feature/ha_agent' into develop

[33mcommit 31dc31e960e1c90aec15bdc22c4cd5a892da36cd[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Mar 13 08:08:33 2026 +0000

    feat(ha): refresh périodique + reload manuel
    
    - ha_agent: refresh loop asyncio toutes les X minutes (HA_REFRESH_INTERVAL)
    - ha_agent: méthode reload() manuelle + on_stop() propre
    - app.py: endpoint POST /ha/reload + injection ha dans set_agents
    - telegram_agent: commande /ha_reload
    - Makefile: fix cible test (suppression dépendance .env)

[33mcommit b760199a50d32ef00cc299b8d1cb859c55dad803[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Mar 13 07:05:30 2026 +0000

    feat(ha): make ha-agent — configuration interactive HA
    
    - Makefile: cible ha-agent interactive (URL + token + test connexion)
    - scripts/ha_setup.py: helper Python pour écrire dans neron.yaml
    - fix: évite les problèmes de caractères spéciaux dans le token

[33mcommit 49c352179552f8937c2fa11e8d546f5ffd486813[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Mar 12 21:44:35 2026 +0000

    feat(ha): smart entity matching + on_start hook + cache states
    
    - BaseAgent: ajout hook on_start()
    - HAAgent: _parse_query avec scoring sur entity_id et friendly_name
    - HAAgent: cache des entités HA au démarrage via on_start()
    - HAAgent: lazy reload si cache vide
    - app.py: await ha_agent.on_start() dans lifespan
    - fix: rstrip('.') sur friendly_name dans _build_response

[33mcommit 901f41601e03b368edad9aa11da681b1787ec418[m
Merge: 69d7d49 0131d11
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Mar 12 20:31:50 2026 +0000

    update Makefile

[33mcommit 0131d11dddd12aef85c6d32d8a4c7a9b882c178e[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Mar 12 18:30:04 2026 +0000

     update Makefile - ajout menu ha-agent

[33mcommit 69d7d4919ac4dec6c93392f04bdb88f2b50298e7[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Mar 12 17:57:32 2026 +0000

    pull Makefile v1

[33mcommit d2e3ff4a5b88fa95a517f9092bc71c65e7829b4f[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Mar 12 11:41:16 2026 +0000

    fix: Makefile start/restart/test utilise if/else au lieu de call macros

[33mcommit 2e54fb292db25c2f08e7f987f00f3c6f836ef469[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Mar 12 08:09:30 2026 +0000

    fix: table events SQLite, modèle llama3.2:1b, Makefile apostrophes et accents

[33mcommit 6757b46f939348a51a767ae187033e7ea9a4471f[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Mar 12 07:56:53 2026 +0000

    refactor: nettoyage structure — suppression dossiers en double

[33mcommit b82ead3881792719474aeeb63bc5807a65eec1a0[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Wed Mar 11 17:03:44 2026 +0000

    fix: correction URL NERON_CORE_URL manquant http:// dans telegram_agent

[33mcommit b21ed28c6c0bfb24c174e865e2a8b3d1eedc5472[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Wed Mar 11 14:10:05 2026 +0000

    fix: logs déplacés vers data/logs, ajout FileHandler dans app.py

[33mcommit 8ce01cf5591eee7d48c699f99203aa3a3f95d3d3[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Wed Mar 11 14:05:44 2026 +0000

    refactor: modules/neron_core → core, chemins data centralisés

[33mcommit 0a7907e3a5f1c376533da2b4128cb897ebc52d72[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Tue Mar 10 19:46:01 2026 +0000

    suppression de public/

[33mcommit 2986d85e21a40ae46610d4abaa8f900561238b08[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Tue Mar 10 09:02:26 2026 +0000

    fix(tests): suppression chemins hardcodés — utilisation Path relatif dans conftest

[33mcommit 59b9b62ba267445682de6a7f93b83a43cffa5d81[m
Merge: f36d5f3 3f699fc
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Tue Mar 10 08:56:40 2026 +0000

    Merge branch 'feature/ha-agent' into develop

[33mcommit 3f699fcc96fe596aa81bd916953426e5f4478ba6[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Tue Mar 10 08:52:36 2026 +0000

    docs: ajout section home_assistant dans neron.yaml.example

[33mcommit 34f5aebcd40a572916e4320960933a1bf9376dac[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Tue Mar 10 08:45:12 2026 +0000

    test(ha-agent): 16 tests HAAgent — parsing, execute, erreurs, connexion

[33mcommit 8607d21a75c422ad702af62b659ebab1887b4b45[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Tue Mar 10 08:40:25 2026 +0000

    feat(ha-agent): ajout HAAgent, branchement HA_ACTION, config HA

[33mcommit e8ef174bc1f5299ce63709bd576d9d4acba0a125[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Tue Mar 10 08:15:18 2026 +0000

    tests: centralise tout dans tests/, adapte STT/TTS/core_response à v2.1

[33mcommit b97ddb19177518999d167d4946b2de4f389c625f[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Tue Mar 10 08:12:13 2026 +0000

    feat(install): ajout détection et installation Home Assistant

[33mcommit f36d5f36f6f59b67d421ce389f8648fa018e16d5[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Tue Mar 10 07:02:39 2026 +0000

    tests: centralise tout dans tests/, adapte STT/TTS/core_response à v2.1

[33mcommit 64cedaca0d20c28de60259d84c683e9cb4fbe48b[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Tue Mar 10 06:23:05 2026 +0000

    test: mise à jour test_neron.py v2.1 — config yaml, reload, TTS skippé

[33mcommit 73a403ede85794f2243bed58134a5fa8064dacdc[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Tue Mar 10 06:15:33 2026 +0000

    feat(ux): intégration système d'affichage animé dans install.sh

[33mcommit 35b8f3f527fbbe66aef981ec3fb085be929454fd[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Tue Mar 10 06:07:55 2026 +0000

    feat(ux): intégration système d'affichage animé dans install.sh

[33mcommit 83832982275f19541d2f40911c168c35769f8677[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Tue Mar 10 05:44:29 2026 +0000

    feat(config): migration Makefile et install.sh vers neron.yaml, suppression .env

[33mcommit 257275d49c0515731cbde27eeb6f57803091c682[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Mar 9 23:35:33 2026 +0000

    chore: suppression package.json et vite.config.ts obsolètes (legacy HUD)

[33mcommit 29a946649119268dcf6310628203fe1daf4b7817[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Mar 9 23:33:49 2026 +0000

    chore: suppression neron_hud obsolète

[33mcommit f4cb3c5c24687f449e05d0207eb1b4f0a440e214[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Mar 9 23:31:07 2026 +0000

    chore: suppression neron_system.py obsolète (remplacé par systemd)

[33mcommit 149f7da9e64d5d76a1d39bab4dd79a58e7e75485[m
Merge: d3f525d 71a6706
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Mar 9 23:27:38 2026 +0000

    Merge branch 'feature/getenv' into develop

[33mcommit 71a670654074604b2be64cc712ca7005210ba240[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Mar 9 23:22:51 2026 +0000

    feat(config): migration complète vers neron.yaml, suppression .env, TTS désactivé temporairement

[33mcommit 9d51bddff00327028ebf7342a93145216ecf3da9[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Mar 9 21:49:14 2026 +0000

     rename neron.yml en neron.yaml

[33mcommit d60bb6bee373e0a53528031a2aff4140b9d052a2[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Mar 9 20:57:21 2026 +0000

    feat(config): migration agents vers settings v2.1.0

[33mcommit d3f525d70c76dc57fe59515c1b200434a4200673[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Mar 9 11:44:11 2026 +0000

     suppression modules obsolete

[33mcommit 2eb34b71b48d07445779e6a61ffa39414b697c9b[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Mar 9 08:10:21 2026 +0000

    feat(config): ajout pyyaml pour neron.yaml

[33mcommit d2b6b10fc8c39ec15043b256343eb4991ad42222[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Mar 9 08:07:20 2026 +0000

    feat(config): app.py migré vers config.py — suppression os.getenv

[33mcommit 599dbd0389f8e115e6fe662e5523c927cb7dc0ee[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Mar 9 07:54:48 2026 +0000

    feat(config): neron.yaml + loader Python v2.1.0
    
    - Config centralisée par section (llm, stt, tts, telegram, watchdog, memory, logs)
    - Fallback automatique .env / variables d'environnement
    - Rétrocompatibilité totale avec v2.0.0
    - print_config() pour neron env / neron doctor

[33mcommit 8ebe66d07f3dc57017cfb0f3c91e2d4a80830186[m
Merge: 7d57ffa 01c68e0
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Mar 9 05:56:03 2026 +0000

    Merge tag 'v2.0.0' into develop
    
    release/v2.0.0

[33mcommit 01c68e038433465c4acdacfe1df7b80cae9bc23b[m[33m ([m[1;33mtag: [m[1;33mv2.0.0[m[33m, [m[1;32mmaster[m[33m)[m
Merge: 70c8d0a 7d57ffa
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Mar 9 05:55:45 2026 +0000

    Merge branch 'release/v2.0.0'

[33mcommit 7d57ffa65988afbe6335247bd58a1a563319916c[m
Author: enabeteleazar <161418955+enabeteleazar@users.noreply.github.com>
Date:   Mon Mar 9 06:52:19 2026 +0100

    docs: README.md v2.0.0 — architecture native sans Docker"

[33mcommit 0cd042b5ba0a5bc32360d575989e354f00df3680[m
Author: enabeteleazar <161418955+enabeteleazar@users.noreply.github.com>
Date:   Mon Mar 9 06:48:43 2026 +0100

    Update QUICKSTART.md

[33mcommit 40d911a9761198f4614f27228e5c162d55adc12b[m
Author: enabeteleazar <161418955+enabeteleazar@users.noreply.github.com>
Date:   Mon Mar 9 06:44:25 2026 +0100

    Update CONTRIBUTING.md

[33mcommit 34306009e5a18c1997569c31a54998ca465e0093[m
Author: enabeteleazar <161418955+enabeteleazar@users.noreply.github.com>
Date:   Mon Mar 9 06:39:53 2026 +0100

    Update CHANGELOG.md

[33mcommit 257877b88d68e0f70e31f9c8a987a72ee1fd2dd8[m
Author: enabeteleazar <161418955+enabeteleazar@users.noreply.github.com>
Date:   Mon Mar 9 06:36:35 2026 +0100

    Update CHANGELOG.md

[33mcommit f526f5fda01537cb2305ff1b8232732c0d40f204[m
Merge: 2d34fd7 70c8d0a
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Mar 9 05:34:14 2026 +0000

    ajoit de public/index.html & public/style.css

[33mcommit 70c8d0aedeb818c65b32c6b38e91035301a5f8ac[m
Merge: 55dd83d ed4f799
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 8 21:07:11 2026 +0000

    Merge branch 'release/v2.0.0'

[33mcommit ed4f799904d16f44587dd93bb3082182c9e3ad27[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 8 21:05:38 2026 +0000

    ajout de la ding page public/index.html

[33mcommit 2cc7d226c63afec2014d7b08f941196b7d5e4df1[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 8 20:12:59 2026 +0000

     mis a jour de Makefile pour PROD

[33mcommit 15b64a01a5630e140be271b20062058bb177c675[m
Author: enabeteleazar <161418955+enabeteleazar@users.noreply.github.com>
Date:   Sun Mar 8 21:16:54 2026 +0100

    Delete start_neron.sh

[33mcommit a075f9c27746d172ace7d34d2925bf94168b826e[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 8 20:07:04 2026 +0000

    modif des variables dans .env & install.sh pour PROD

[33mcommit 2d34fd7029d164566d773b3be595e11623d1fb92[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 8 20:00:22 2026 +0000

     deplacelent de index.hrml dans public

[33mcommit e3ecb3d472eefda0ef8240b394a61e2e3a35911f[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 8 19:45:13 2026 +0000

    feat: add landing page

[33mcommit fd353542636ff383b7e7d7fbbe34ca65cd0537c7[m
Merge: 6944e16 6511efe
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 8 19:27:55 2026 +0000

    Merge branch 'feature/install' into develop

[33mcommit 6511efe8ba6aca1804862ddb87f044859896b483[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 8 18:57:48 2026 +0000

    suppression pthon3.12 su makefile

[33mcommit 6be2cc59e52b4fe38a627f00d24d869ff9755224[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 8 18:07:06 2026 +0000

    fix: ajout zstd dans dépendances

[33mcommit f84e829a20cfe0a08e76d692a4491e1246b34c83[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 8 17:47:14 2026 +0000

    update dev -> install.sh

[33mcommit 00f055f2770909644edf37faafe7c8f059284198[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 8 17:19:15 2026 +0000

    fix: détection version Python dynamique — fallback python3-venv

[33mcommit 6e2c20c931a448432576f4c59c57a6a6587c0345[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 8 16:51:39 2026 +0000

     ajout e la dependance zstd

[33mcommit bf85d59556c8591b1bfaecc90aa4d0792f4eeea9[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 8 15:32:16 2026 +0000

    fix: bot Telegram optionnel — démarre sans token

[33mcommit 3ba715f1e1c1c05ee2b6374cad7e50d3baf7bc85[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 23:36:49 2026 +0000

     update DEV -> install.sh

[33mcommit 96f4cf5bcfbf29ab37cfb0a3dd16076e03e3584a[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 23:30:41 2026 +0000

    fix: StartLimitIntervalSec déplacé dans [Unit]

[33mcommit fda49716d9f01814659408767f1699e9ee3fbea3[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 23:22:20 2026 +0000

    suppresion de 5b et instal ollama regroupé

[33mcommit 0f6bd472adb780d3e24e1d5f9f5e96d36d3b0e97[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 23:10:52 2026 +0000

    indentation DEV:

[33mcommit 72e3c859bee799c08dd6d265370c6d2d5cbcd7c0[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 23:05:10 2026 +0000

    fix: BRANCH lu depuis .env avant clone

[33mcommit 3af4ac8570371f5217326b51d010d7a4a8dc2a86[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 23:01:43 2026 +0000

    fix: NERON_DIR=/etc/neron partout

[33mcommit 90651050a952c83b779546e80eb6c6344a5d5245[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 22:59:52 2026 +0000

    feat: NERON_BRANCH dans .env.example

[33mcommit 3ccda3e5f6e77b84b0de69312c7b70465d5332f1[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 22:54:49 2026 +0000

    .

[33mcommit 3cdd78a375209e27642e0deb4d5af78dfe4d64cb[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 22:49:05 2026 +0000

    update install.sh

[33mcommit 476c49d5312c01990c4730720fb5e366353eccfd[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 22:45:54 2026 +0000

    fix: .env créé avant clone — NERON_DIR disponible dès le départ

[33mcommit 3b006cc0a47dfd2318c21fd30cd7feff9fb1d71b[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 22:41:09 2026 +0000

    fix: debug clone — afficher contenu dossier si Makefile introuvable

[33mcommit 67f6f26beecfe8eaa955e90d5d64705d77983790[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 22:39:09 2026 +0000

    revert: BASE_DIR dynamique — NERON_DIR dans .env causait échec clone

[33mcommit 0abd699f9572f9e468d45f2a76242eb6ed3b1389[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 22:34:00 2026 +0000

    affichage numero DEV

[33mcommit c70961457af9f5a8bc0fc0c78c6c5e6cf4f63567[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 22:17:43 2026 +0000

    fix: NERON_DIR mis à jour dans .env selon INSTALL_DIR réel

[33mcommit 5f6ece93fcb47dc8801e012603a867f994e02fd2[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 22:16:03 2026 +0000

    feat: Makefile lit NERON_DIR depuis .env

[33mcommit beddd601d3b338e5392ca0d8800050bec9a05a1c[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 22:15:34 2026 +0000

    feat: NERON_DIR dans .env.example + lu dans install.sh

[33mcommit 0b4b63ede63a29c860623bae8154f9c945a7f163[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 22:12:44 2026 +0000

    fix: set +e dans mode --telegram-only

[33mcommit 89b953708a2a8948f5156adb8a632a3cc7ec4b42[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 22:11:59 2026 +0000

    fix: token vide + getUpdates chat_id

[33mcommit 81dc894e8a7bc93fd36e00569f7782ac12de4d98[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 22:08:56 2026 +0000

    fix: couleurs définies dans mode --telegram-only

[33mcommit decbfd92d882ccfe74de4b057b2d68a563ab6895[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 22:07:33 2026 +0000

    fix: watchdog config uniquement si WATCHDOG_ENABLED=true

[33mcommit 1d61d4c7294c780b5eded533fa53d72c7ae90e56[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 21:53:13 2026 +0000

    feat: watchdog désactivé par défaut — WATCHDOG_ENABLED=false

[33mcommit 98a84296f8ac63f5e33b170c09ac45ac7e0e8e46[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 21:48:34 2026 +0000

    fix: setup_telegram définie avant appel --telegram-only

[33mcommit 526cc37d3545020d8496dd79d917f8b630de7400[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 21:47:53 2026 +0000

    fix: install.sh --telegram-only évite relance complète

[33mcommit c3d75f9fa6f47c659b9d677fa4fb663c1672d883[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 21:44:47 2026 +0000

    refactor: fusion model + model-set → make ollama

[33mcommit 5cb3f6334bb58645af4e7aae7d33bf63f5dae741[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 21:42:34 2026 +0000

    feat: make telegram dans menu help

[33mcommit 03f2347bdda4ca96380ade5b401a457806980d6a[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 21:41:45 2026 +0000

    feat: configuration Telegram interactive dans install.sh + make telegram

[33mcommit b3d2c860303767389186a7fbb26ffcfbe1b5f4e4[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 20:35:22 2026 +0000

    feat: make install — ollama serve + pull modèle auto

[33mcommit 324e4c32dbf9ba30eece5120d856f4888b87c320[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 19:36:39 2026 +0000

    fix: service Ollama dans install.sh + data/ dans Makefile

[33mcommit 0d70e3dbeb383c640833108ab20700444b0dacca[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 18:06:03 2026 +0000

    ajout de numero de version - install.sh

[33mcommit ff214b3f877d68d4ddf7e1b4648246ae0e0ecff9[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 18:01:10 2026 +0000

    fix: INSTALL_DIR /opt/neron + chown dans make install

[33mcommit 20edfef7f471e3a33a573c9080cebfabc6efd882[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 17:52:45 2026 +0000

    fix: clone verbeux + fallback sans sudo

[33mcommit a158c8c8eb1c4afb684c97621b03f6797cf8e506[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 17:51:04 2026 +0000

    fix: clone git robuste + vérification Makefile

[33mcommit cb94aeaa0b0ec92c3ca9376dacf1101c39a3b028[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 17:41:40 2026 +0000

    fix: branche par défaut master

[33mcommit f7d4a4c18af7c183a8d80581d8b5a9b1a64ce3d7[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 17:37:38 2026 +0000

    fix: branche par défaut feature/install pour tests

[33mcommit 32400ee89d61424bd31b1e61b09ea40032aea4dc[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 17:32:03 2026 +0000

    fix: BASE_DIR dynamique dans Makefile — plus de chemin absolu

[33mcommit 7ff8c7e6938bc02c3f0bc13b2fe4835c81ca3f9e[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 17:29:19 2026 +0000

    feat: install.sh v2 - bootstrat amelioré

[33mcommit 6944e16e23f490cb2d6d9242542c04e79668c806[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Mar 7 17:22:13 2026 +0000

    chore: Supppression neron_watchog/neron_telegram - module Docker obsolete

[33mcommit bcb25d9c547ca5cbf9217af2e433a664ab776b6c[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Mar 6 13:48:51 2026 +0000

    refactor: suppression complète des chemins absolus
    
    - Tous les chemins /mnt/usb-storage/Neron_AI remplacés
    - Chemins relatifs via __file__ dans les agents Python
    - BASE_DIR dynamique dans Makefile
    - NERON_DIR configurable dans install.sh
    - neron.service avec placeholders __NERON_DIR__/__NERON_USER__

[33mcommit 301cc57e3619d971e46c8f1d9073cafe187e4381[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Mar 6 13:47:52 2026 +0000

    fix: chemins relatifs corrects — 4x dirname depuis agents/

[33mcommit e886409e0349409d412a006a0c0477e05f74a828[m
Merge: ff753f4 4cf0a7b
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Mar 6 13:38:21 2026 +0000

    Merge branch 'feature/makefile' into develop

[33mcommit 4cf0a7be20a85f1fcac8f26bb4f2255c93618776[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Mar 6 13:37:52 2026 +0000

    feat: chemins dynamiques — plus de chemins absolus
    
    - neron.service : placeholders __NERON_DIR__ et __NERON_USER__
    - make install : génère neron.service avec sed au déploiement
    - Makefile : BASE_DIR dynamique depuis emplacement du Makefile
    - install.sh : INSTALL_DIR configurable via NERON_DIR

[33mcommit 6366c7b7cacb9ae79241521d47436f88909bbcc8[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Mar 6 13:34:26 2026 +0000

    feat: chemins dynamiques — plus de chemins absolus
    
    - neron.service : placeholders __NERON_DIR__ et __NERON_USER__
    - make install : génère neron.service avec sed au déploiement
    - Makefile : BASE_DIR dynamique depuis emplacement du Makefile
    - install.sh : INSTALL_DIR configurable via NERON_DIR

[33mcommit 77521b8add0fd9e7e137de6fd3f6bbe40e3a69dd[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Mar 6 12:57:48 2026 +0000

    feat: install.sh + Makefile + .env.example v2
    
    - install.sh : one-liner curl | bash
    - Makefile : make install/start/stop/restart/logs/update/clean
    - .env.example : mis à jour pour v2 (Telegram, Ollama, Watchdog)
    - Suppression références Docker obsolètes

[33mcommit ff753f46bc44e5c925dcea654455cbdb6d459399[m
Merge: c8a9f77 5ce1142
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Mar 6 12:43:03 2026 +0000

    Merge branch 'feature/watchdog' into develop

[33mcommit 5ce1142ec26370287619b3af01e42b469b724a71[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Mar 6 12:41:29 2026 +0000

    feat: Watchdog /help et /config améliorés v2.10
    
    - /confirm /cancel retirés du menu (commandes internes)
    - /mute /config /clear ajoutés dans Actions
    - /config : descriptions claires pour chaque seuil
    - Température CPU dans /status et alertes

[33mcommit a75912a8d09e35c09a8f17aae92ae0094da806bc[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Mar 6 12:26:57 2026 +0000

    feat: Watchdog alerte température CPU v2.8
    
    - _get_cpu_temp() : lecture coretemp/acpitz via psutil
    - Alerte si temp > 75°C (configurable via WATCHDOG_CPU_TEMP_ALERT)
    - Température affichée dans /status
    - Température affichée dans /stats
    - /config temp <valeur> pour modifier le seuil

[33mcommit a4a6b810ad65983136d71c84b5f460a355a5d87a[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Mar 6 11:46:13 2026 +0000

    feat: start_neron.sh menu interactif v2
    
    - Menu : Install / Start / Stop / Restart / Logs / Status / Quitter
    - Install : apt deps (espeak, ffmpeg, python3-venv...) + venv + pip + systemd
    - Start/Stop/Restart via systemctl
    - Logs via journalctl -f
    - Statut avec RAM et PID

[33mcommit 4fdddab1b6d98f2f27fea5eca0981be2ab0db39b[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Mar 6 11:48:46 2026 +0100

    feat: systemd + start_neron.sh v2
    
    - neron.service : démarrage auto au boot, restart si crash
    - start_neron.sh : utilise systemctl au lieu de python3 direct
    - Logs via journalctl
    - Plus de PID file manuel

[33mcommit 53c353a452cdc1b3fba0e9633baa0031164583e6[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Mar 6 11:46:06 2026 +0100

    feat: service systemd neron.service
    
    - Démarrage automatique au boot
    - Restart automatique si crash (RestartSec=10)
    - Logs vers logs/neron_core.log
    - After=network.target ollama.service

[33mcommit 1f093fe5ad6045a2f919c52435c35f240aaba88b[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Mar 6 11:43:37 2026 +0100

    feat: Watchdog v2.7 complet
    
    - /config — voir/modifier seuils en live
    - /mute <min> — couper alertes temporairement
    - /clear — effacer historique events (avec confirmation)
    - /uptime /history /logs /stats /trend recréés
    - /rapport /hebdo fonctionnels
    - Menu /help reorganisé par catégories
    - Toutes fonctions _wdog_cmd_* restaurées

[33mcommit 12f4132bb38768d3045c93d7fc1755a91a24bea4[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Mar 6 10:29:21 2026 +0000

    feat: Watchdog rapport hebdomadaire v2.6
    
    - _send_weekly_report() : rapport complet 7j
    - Envoi automatique lundi 08h00
    - /hebdo : forcer rapport hebdomadaire immédiat
    - Stats : crashs, recoveries, auto-restarts, interventions
    - Tendance vs semaine précédente
    - Agents les plus touchés

[33mcommit 1c6ad6181dac2a8be8649f7000bba5b4299b3727[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Mar 6 10:25:13 2026 +0000

    feat: Watchdog alertes intelligentes v2.5
    
    - Alerte RAM process > 500MB (memory leak)
    - Alerte Ollama silencieux > 10min
    - Alerte Néron silencieux > 24h
    - Anti-spike CPU : alerte seulement après 3 checks consécutifs
    - Délai de grâce 2min au démarrage
    - Seuil CPU monté à 95% via WATCHDOG_CPU_ALERT
    - _last_conversation mis à jour à chaque message Telegram

[33mcommit 07baa5ab44dceed5f31573aae62995afbe8e12ab[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Mar 6 09:02:48 2026 +0100

    feat: séparation nette des deux bots Telegram
    
    - @HomeBox_Neron_bot : conversations + /memory uniquement
    - @Neron_Watchdog_bot : monitoring complet
    - Suppression /start /help /status /score /anomalies de Neron bot
    - Watchdog observabilité : /logs /stats /trend /rapport

[33mcommit dd0a2ac3ae52d56a9ea119c9158adcab66f085b1[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Mar 6 08:52:59 2026 +0100

    feat: Watchdog sécurité v2.2
    
    - /restart core avec confirmation /confirm + /cancel
    - Expiration confirmation 30s
    - os.execv pour vrai restart process
    - /confirm /cancel dans le menu /start

[33mcommit 7f820178dfc631d0e485bfd86a4b2e3c3a3229b5[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Mar 6 08:45:11 2026 +0100

    feat: Watchdog v2.1 complet
    
    - /uptime et /history dans le menu /start
    - Rapport quotidien 08h00 testé et fonctionnel
    - psutil ajouté aux requirements
    - Auto-restart agents (3 échecs / 5min)
    - Notifications démarrage/arrêt Telegram

[33mcommit 920472720edea104bda54d26b16438c6621e1dcc[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Mar 6 08:37:01 2026 +0100

    feat: Watchdog v2 complet + /restart agents
    
    - watchdog_agent.py : bot @Neron_Watchdog_bot dédié
    - /status : Core + Ollama + LLM + STT + TTS + Mémoire
    - /restart <agent> : reload live sans redémarrer le process
    - /score /anomalies /help
    - reload() ajouté sur tous les agents
    - start_neron.sh : chargement .env robuste (commentaires inline)

[33mcommit de26a1d0778cdc83c2632546cae50b22091492a3[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Mar 6 07:19:56 2026 +0000

    feat: Watchdog natif v2 + bot @Neron_Watchdog_bot
    
    - watchdog_agent.py : monitoring CPU/RAM/disk + détecteur anomalies
    - Bot @Neron_Watchdog_bot : /status /score /anomalies
    - Bot @HomeBox_Neron_bot : /score /anomalies ajoutés
    - Table events SQLite pour historique watchdog
    - Deux bots Telegram dans un seul process :8000

[33mcommit c8a9f77531fcd5a311cbddf7af595ade886755a0[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Mar 6 06:44:56 2026 +0000

    chore: suppression module neron_web (Gradio Docker-era)
    
    - Interface web Gradio supprimée (remplacée par Telegram)
    - Plus de dépendance gradio/huggingface-hub

[33mcommit 97246617881125839309aa26d44b79ade395e8c8[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Mar 6 06:42:34 2026 +0000

    chore: suppression gradio (interface web Docker-era)
    
    - gradio retiré de requirements.txt
    - typer désinstallé (dépendance transitive gradio)
    - Plus de WARNING au démarrage

[33mcommit a06a21d9dfd97d9cdc4b4b33ef52642317390088[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Mar 6 06:37:04 2026 +0000

    fix: start_neron.sh — logs fichier + mkdir logs/
    
    - Redirection stdout/stderr vers logs/neron_core.log
    - mkdir -p logs/ au démarrage
    - tail avec sleep 2 pour attendre le fichier

[33mcommit 58d1f4a680f2a58516381a13804ef8670b260d1b[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Mar 6 06:13:11 2026 +0000

    fix: TTS simplifié — espeak CLI pur, sans pyttsx3
    
    - Suppression init pyttsx3 (save_to_file générait 0 bytes)
    - espeak CLI direct avec voix 'fr' et rate configurable
    - Plus de sélection de voix via pyttsx3

[33mcommit 8a5eb98ec6afa26122137d0e6089e3f6a0d90b12[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Mar 6 05:58:31 2026 +0000

    fix: TTS espeak CLI + router normalisation accents
    
    - engine.py : pyttsx3 save_to_file → espeak CLI direct (WAV non vide)
    - intent_router.py : normalisation Unicode avant matching (météo → meteo)
    - test_neron.py : 25/25 tests passés

[33mcommit a4dd02d1a2900cccfe4573fe56c23ad194768052[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Mar 6 05:38:14 2026 +0000

    update llm_agent.py

[33mcommit dcf8f32a64789d4338b48ee6131a37b8dcc197fa[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Mar 6 05:37:10 2026 +0000

    test: refonte suite de tests pytest v2.0
    
    - Suppression anciens scripts bash (Docker-era)
    - Suppression dossiers vides e2e/ integration/
    - Nouveau test_neron.py : Memory, LLM, STT, TTS, Router
    - pytest.ini : asyncio_mode=auto

[33mcommit 298415fdab29cc9887954aba09e4df9585c38954[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Mar 5 23:04:50 2026 +0000

    refactor: suppression ports internes — appels directs natifs
    
    - LLMAgent : httpx neron_llm:5000 → Ollama localhost:11434 direct
    - STTAgent : httpx neron_stt:8001 → faster-whisper direct
    - TTSAgent : httpx neron_tts:8003 → pyttsx3 direct
    - MemoryAgent : httpx neron_memory:8002 → SQLite direct
    - app.py : suppression import httpx, init séquencielle des moteurs

[33mcommit 051884d76bac9281ed381245fb9ad9db8cb285f8[m
Merge: f9f024b c6bccdb
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Mar 5 22:45:10 2026 +0000

    Merge branch 'feature/remove-docker' into develop

[33mcommit c6bccdba6b8e53a4ff4cfdfcff18118d13f6bea9[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Mar 5 22:44:43 2026 +0000

    chore: refonte start_neron.sh v2.0 style v1.17

[33mcommit 73ed42dd1b56f4bdc32b1d5eec3d7bdfd2b7196e[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Mar 5 22:34:42 2026 +0000

    chore: nettoyage post-migration
    
    - Suppression neron_system/ (dossier vide)
    - Suppression modules/requirements.txt (remplacé par racine)
    - Suppression patch_app.py (script migration terminée)
    - Suppression fichiers audio test (output.wav, test.wav)
    - Déplacement simulate.py → tests/
    - Nettoyage .gitignore (doublons)

[33mcommit a80e9f2019ff8f63621f4be06d97b32989fed36d[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Mar 5 22:30:36 2026 +0000

    feat: migration Docker → natif Ubuntu
    
    - Suppression tous les Dockerfiles et docker-compose
    - Suppression requirements.txt par module (unifié à la racine)
    - Ajout neron_system.py (monolithe multiprocessing)
    - Ajout requirements.txt unifié (45 dépendances)
    - Correction app.py memory et stt (chemins natifs)
    - Correction start_neron.sh (suppression sudo/apt)
    - Mise à jour .gitignore (data/, venv/, guillemets)

[33mcommit f9f024bed7f9ea27203e31b185e70a4fdbd76833[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Mar 5 20:48:26 2026 +0000

    retrait de ollama du system docker -> natif

[33mcommit 6ab50a9877499b8993834664412a70fd5053b7ad[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Wed Mar 4 07:20:55 2026 +0000

    Update .gitignore

[33mcommit fab389f424f6abb7dc6f06912ea660276fc0ec7a[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 1 20:41:28 2026 +0000

    fix(watchdog): Web Voice SSL + config Telegram/Watchdog - tous services OK

[33mcommit d01d1ef044b030135c28a7e531c4e4fdf9f90e00[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 1 20:07:45 2026 +0000

    feat(streaming): LLM streaming SSE - neron_llm + neron_core + neron_telegram

[33mcommit 58f8cf84b5fea9c2b354cd9879b64fd774335362[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 1 19:31:20 2026 +0000

    feat(time): adaptive response - heure seule, date seule, ou les deux

[33mcommit 4093735c26d7ec34f2ba983fd40c2c93ad077428[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 1 19:22:19 2026 +0000

    feat(memory): conversational memory - short term + long term context injection

[33mcommit f48873dd1643d5ddc4c4f8a12c250395bb4eebfa[m[33m ([m[1;33mtag: [m[1;33mv1.17.0[m[33m)[m
Merge: 6b9f882 55dd83d
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 1 15:17:37 2026 +0000

    Merge tag 'v1.17.0' into develop
    
    release v1.17.0

[33mcommit 55dd83dd0ffd50fb989650ebd805b90adfc97226[m
Merge: 9c956a0 5a6ca6f
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 1 15:17:29 2026 +0000

    Merge branch 'release/v1.17.0'

[33mcommit 5a6ca6f8b99aeb66140f26363bddb3d3c5e17a8d[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 1 15:16:59 2026 +0000

    docs: update CHANGELOG v1.17.0

[33mcommit 6b9f882abd43c77b0583417b48494d6208b65af7[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 1 14:55:52 2026 +0000

    feat(telegram): add /url command to get HUD Cloudflare URL

[33mcommit 2b6c09b17863a3b91665efd7ff4c14e3a1d34da5[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Mar 1 14:20:44 2026 +0000

    feat(hud): add neron_hud module - STT, chat, metrics, animation

[33mcommit 732ffd95eec0b9811fcf3250a28e9d24cc208957[m
Merge: 4f6be53 5d13db2
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 28 23:51:24 2026 +0000

    Merge branch 'feature/neron_hub' into develop

[33mcommit 5d13db2d8c3bebb72d90f60a6f138dba5b93a944[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 28 23:19:59 2026 +0000

     utiisation d'feych vanilla

[33mcommit da1f96f7771bdcb375a32725ec7ae7d15c694869[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 28 17:41:32 2026 +0000

    feat: neron_hud v3 - vanilla CSS, no tailwind, build OK

[33mcommit 4f6be535bd6d398e1a7dd9ba22b864bbd1a10bd4[m[33m ([m[1;33mtag: [m[1;33mv1.16.0[m[33m)[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Feb 27 13:40:41 2026 +0000

    add readme -> Watchdog UP

[33mcommit bec00c747472ae9583f3952017006d9f3a5bc657[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Feb 27 11:30:59 2026 +0000

    update CHANGELOG & start_neron

[33mcommit 00aa261d06cd2e84749ee2793801ecbb6be51296[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Feb 27 11:27:27 2026 +0000

    fix: /logs et /history visibles dans le menu /start Telegram

[33mcommit 92c116f0582b8baa51d6fb6cce70006e9504371d[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Feb 27 11:19:59 2026 +0000

    fix: endpoint /logs via socket Docker + HTTPException import watchdog

[33mcommit 02870906039bf7306dc5c6c2c589947b4e8a6c6b[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Feb 27 08:49:09 2026 +0000

    feat: volumes hot-reload app.py pour telegram/watchdog/core - plus besoin de rebuild

[33mcommit 2b4cfc2ec51c00a9cf6c53805a86e305890468cf[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Feb 27 08:26:02 2026 +0000

    feat: volumes persistants sur USB - watchdog JSONL + memory SQLite -> /mnt/usb-storage/Data/

[33mcommit 21e4e5f7e7c94cfb2ad9834a3554583eb26e6f78[m
Merge: e79d4c5 9c956a0
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Feb 27 00:16:48 2026 +0000

    Merge tag 'v1.15.0' into develop
    
    release v1.15.0

[33mcommit 9c956a004db3feb682eaf1c0f12687de2234a2db[m[33m ([m[1;33mtag: [m[1;33mv1.15.0[m[33m)[m
Merge: 7e24272 7f46a5c
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Feb 27 00:16:35 2026 +0000

    Merge branch 'release/v1.15.0'

[33mcommit 7f46a5c01aefe31a54fcc8267694d63c41bb125e[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Feb 27 00:15:16 2026 +0000

    release v1.15.0

[33mcommit e79d4c5ef451862f7b357a238b0d9db23dbd58ee[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Feb 27 00:11:32 2026 +0000

    feat: score santé + tendance hebdomadaire dans rapport quotidien + pause auto rebuild

[33mcommit 148ec2f8b7e0c235123116f56ca43c51c93412d5[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 23:59:04 2026 +0000

    feat: pause automatique watchdog pendant rebuild Docker + reprise auto 60s

[33mcommit 9135e104a29f18e23e7513ffaa367cb642d45e3a[m
Merge: 9a4de15 7e24272
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 23:22:08 2026 +0000

    Merge tag 'v1.14.0' into develop
    
    release v 1.14.0

[33mcommit 7e2427242a3c16477bde0c66e2a3c295a0ccf349[m[33m ([m[1;33mtag: [m[1;33mv1.14.0[m[33m)[m
Merge: 2a81f81 ab16950
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 23:21:53 2026 +0000

    Merge branch 'release/v1.14.0'

[33mcommit ab169503b93d40ca3075b9e9124654465d282951[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 23:20:23 2026 +0000

    release v1.14.0

[33mcommit 72bcaddcc2fe458d009fffacbd12e668c42d132b[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 23:18:12 2026 +0000

    docs: changelog v1.14.0 - neron_telegram + API HTTP watchdog

[33mcommit 9a4de15c8ec88eca89dd138cb24f1ee6c4bdd1ec[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 23:11:55 2026 +0000

    feat: API HTTP watchdog + commandes Telegram /status /stats /score /anomalies /restart /pause /resume

[33mcommit 2b5c5286081cce43f052f4c0dab2db504d53c962[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 22:38:10 2026 +0000

    feat: neron_telegram - bot bidirectionnel, commandes /status /stats /score /anomalies /restart /pause /resume

[33mcommit 15df90b0ed3f703dca2ee00aa9059ab84cc15d72[m
Merge: 98f40d4 2a81f81
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 21:39:22 2026 +0000

    Merge tag 'hotfix-watchdog' into develop
    
    hotfix-watchdog

[33mcommit 2a81f81e013a59d76255c80f897232c49455012a[m[33m ([m[1;33mtag: [m[1;33mhotfix-watchdog[m[33m)[m
Merge: 2275c4b 0aa9f25
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 21:38:53 2026 +0000

    Merge branch 'hotfix/hotfix-watchdog'

[33mcommit 0aa9f251474eaccdd1ac5dbcb1c59ace0dfb4dbd[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 21:37:34 2026 +0000

    fix: ajout méthode record_container_stats manquante dans StrategicMemory

[33mcommit 98f40d4719d09a87756b1dacce4a2b2eaedab311[m
Merge: 9523bf7 2275c4b
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 19:35:13 2026 +0000

    Merge tag 'v1.13.2' into develop
    
    release/v1.13.2

[33mcommit 2275c4bf8c4ed38110c93d9b7c2082f21ff91d73[m[33m ([m[1;33mtag: [m[1;33mv1.13.2[m[33m)[m
Merge: b1b5364 b6c655b
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 19:35:00 2026 +0000

    Merge branch 'release/v1.13.2'

[33mcommit b6c655bce4faab943bd6401ba27b718d0e7f7144[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 19:34:20 2026 +0000

    release: v1.13.1 - watchdog complet, API Key, stats Docker, anomalies, rapport quotidien

[33mcommit 9523bf786f5c956263847d63e029969c0cbfcfc8[m
Merge: 9353e0d f2c53b0
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 19:26:52 2026 +0000

    Merge branch 'feature/auth-api-key' into develop

[33mcommit f2c53b0ac981016fe4ab0452e08e0e4423fe32d7[m[33m ([m[1;33mtag: [m[1;33mv1.13.1[m[33m)[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 19:19:28 2026 +0000

    feat: API Key propagée à neron_web_voice

[33mcommit e538f75491ff6dab6b0f93a55d214552602712b1[m[33m ([m[1;33mtag: [m[1;33mv1.13.0[m[33m)[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 19:01:28 2026 +0000

    feat: authentification API Key - protection endpoint /input/text

[33mcommit 9353e0d501cb275946bb5e7a18bffb1806e8fdfa[m
Merge: c6e6a70 31a476b
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 18:13:09 2026 +0000

    Merge branch 'feature/watchdog-docker' into develop

[33mcommit 31a476bea86c9dd7cf642d5ae61c9157c436bc1d[m[33m ([m[1;33mtag: [m[1;33mv1.12.2[m[33m)[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 18:10:28 2026 +0000

    feat: collecteur Docker complet - stats JSONL, détecteurs memory leak et corrélation CPU/RAM réels

[33mcommit 9ab1155a53e507e77b4e22aecee5e1060625dae5[m[33m ([m[1;33mtag: [m[1;33mv1.12.0[m[33m)[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 17:53:56 2026 +0000

    feat: stats Docker par conteneur - CPU/RAM/réseau, alertes seuils, collecte toutes les 5min

[33mcommit c6e6a7066ec62b4f69bfa61179afb65279ea3807[m[33m ([m[1;33mtag: [m[1;33mv1.11.0[m[33m)[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 17:49:10 2026 +0000

    feat: détection anomalies 12 patterns - récurrent, cascade, memory leak, score santé, tendance hebdo

[33mcommit a037db7c2639ab0f13a68dc0c00a3b2be77f1c28[m[33m ([m[1;33mtag: [m[1;33mv1.10.0[m[33m)[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 17:37:37 2026 +0000

    feat: rapport quotidien 19h - uptime%, crashs, services instables

[33mcommit 0d819b18e1f32e8e97216b35ac78b7ed7df97d96[m[33m ([m[1;33mtag: [m[1;33mv1.9.0[m[33m)[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 15:35:53 2026 +0000

    feat: mémoire stratégique JSONL - journal crash/restart/recovery/instabilité, rétention 30j

[33mcommit 9d2fcfb74115101ef8484e999834921b1658dee0[m
Merge: 6077de8 1eafada
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 14:03:10 2026 +0000

    Merge branch 'feature/watchdog' into develop

[33mcommit 1eafadafe87e890021be357526def00276549564[m[33m ([m[1;33mtag: [m[1;33mv1.8.2[m[33m)[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 14:02:43 2026 +0000

    fix: ignorer événements Docker antérieurs au démarrage, verrou anti-restart concurrent

[33mcommit d8033adc99f25e83ff609ba4398399981a97efba[m[33m ([m[1;33mtag: [m[1;33mv1.8.1[m[33m)[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 13:49:34 2026 +0000

    refactor: renommage neron_control → neron_watchdog, Control Plane → WatchDog

[33mcommit ea8a85232555ee3db447840c057d0c7d88548ad0[m[33m ([m[1;33mtag: [m[1;33mv1.8.0[m[33m)[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 13:39:18 2026 +0000

    feat: watchdog autonome finalisé - restart silencieux, alerte instabilité 3 crashs/10min, zéro doublon

[33mcommit f8da83ca959606222f43ba76820183aabbcd1d50[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 10:59:42 2026 +0000

    feat: watchdog auto-restart instantané - pipeline complet DIE→alerte→restart→récupération

[33mcommit 6077de857c3d0d610f4ccc3e3a5758465bb7e32d[m
Merge: 5fb24a5 b1b5364
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 07:37:47 2026 +0000

    Merge tag 'v1.7.4' into develop
    
    v1.7.4

[33mcommit b1b5364663f6bcde63e1f507e129c08ec43289ce[m[33m ([m[1;33mtag: [m[1;33mv1.7.4[m[33m)[m
Merge: 45bde0a 2a82cd2
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 07:37:31 2026 +0000

    Merge branch 'release/v1.7.4'

[33mcommit 2a82cd2e3b0e139af5ff67870546e655d5dae9b5[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 07:36:55 2026 +0000

    release v1.7.4

[33mcommit 5fb24a5b8c6e6314ddae09c429b2623c3354d36d[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 07:27:28 2026 +0000

    feat: collecteur métriques système - CPU/RAM/disques avec seuils d'alerte

[33mcommit e84f381da80490b95826ea816341535f25835f15[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 07:06:04 2026 +0000

    feat: watchdog Docker Events - détection instantanée DOWN/UP via socket Unix

[33mcommit 1900e23b87f5af8e9f52944c127b9f0937c3e65c[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 06:13:27 2026 +0000

    feat: suppression neron_web - neron_web_voice est la seule interface

[33mcommit 87f3248585cfc7671c3f2321e519f198569be929[m
Merge: 5cb64ec 2a68f93
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 05:42:14 2026 +0000

    Merge branch 'feature/neron_control' into develop

[33mcommit 2a68f9323727db3dbbdc457d634d316d7cb2eeb3[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 26 05:41:12 2026 +0000

    update -> v1.7.4

[33mcommit 7e2808944720be49b5d68810f922d4712426f471[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Wed Feb 25 22:47:21 2026 +0000

    fix: neron_control - ajout neron_internal network, 8 services configurés, ssl_verify, health_path

[33mcommit 7adfc2ed62bffaa86a56d56f6804dba764f340df[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Wed Feb 25 19:17:29 2026 +0000

    ajout du module neron_control

[33mcommit 5cb64ecccb154a913528efb01c4fc3cdcb52f014[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Wed Feb 25 18:08:53 2026 +0000

    Merge tag 'certificat' into develop

[33mcommit e21af92c719eb0a9d6495dc7f4eaf0dff5f5c461[m
Merge: 5129316 45bde0a
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Tue Feb 24 05:36:41 2026 +0000

    Merge tag 'certificat' into develop
    
    certificat

[33mcommit 45bde0aec901af14998898257c473ac0f964ca1a[m[33m ([m[1;33mtag: [m[1;33mcertificat[m[33m)[m
Merge: a3d0d45 b262cd3
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Tue Feb 24 05:36:30 2026 +0000

    Merge branch 'hotfix/certificat'

[33mcommit b262cd30b22f2956932ada9621b493cb497a46d5[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Tue Feb 24 05:36:07 2026 +0000

    fix: update start_neron

[33mcommit 6928148e2d7854b28ba231123eb900224bb417c0[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Tue Feb 24 05:34:40 2026 +0000

    fix: deverrouillage TTS Safari iOS et route certificat
    
    - Ajout unlock SpeechSynthesis au moment du tap utilisateur
    - Route /cert.pem avec Content-Type application/x-x509-ca-cert
    - Regeneration certificat avec SAN IP pour iOS
    - Page tts-test.html pour diagnostic

[33mcommit 512931610762d4dc8a79ebbd2bb2e54ae732d769[m
Merge: 26af0f8 a3d0d45
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Feb 23 22:13:24 2026 +0000

    Merge tag 'docker' into develop
    
    ajout du certificat

[33mcommit a3d0d45a308e137ebb8351e8eec93202b4e56ec1[m[33m ([m[1;33mtag: [m[1;33mdocker[m[33m)[m
Merge: a88e866 ab16ab5
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Feb 23 22:13:08 2026 +0000

    Merge branch 'hotfix/docker'

[33mcommit ab16ab50598e4cab4708e2cf5c603d1b64a610d5[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Feb 23 22:12:51 2026 +0000

    fix: ajout du certificat dans public pour installation iOS
    
    - cert.pem accessible via https://<ip>:8080/cert.pem
    - Necessite reinstallation du profil sur iPhone apres regeneration

[33mcommit b7b5d032db2a607b9b801f5d2134192da3e6cb1f[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Feb 23 21:19:40 2026 +0000

    fix: correction syntaxe Dockerfile neron_stt
    
    - Ajout du # manquant en debut de commentaire

[33mcommit a88e866b74a48466de48a6daffd1c97bcdf2bc9b[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Feb 23 21:13:53 2026 +0000

    fix: conversion neron_web_voice de submodule en dossier normal
    
    - Suppression du submodule fantome
    - Ajout de tous les fichiers du module neron_web_voice

[33mcommit 26af0f8ac13fed2427c75326633212b9af48331a[m
Merge: 944c74f 27ad432
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Feb 23 20:56:23 2026 +0000

    Merge tag 'v1.7.0' into develop
    
    v1.7.0

[33mcommit 27ad43227eb7dc1ce073d4818dc7fdf8e88cbedb[m[33m ([m[1;33mtag: [m[1;33mv1.7.0[m[33m)[m
Merge: 9a56742 2f32ddf
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Feb 23 20:55:13 2026 +0000

    Merge branch 'release/v1.7.0'

[33mcommit 2f32ddf40198b2bf73d6a21cfa81270914169944[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Feb 23 20:55:08 2026 +0000

     update version -> start_neron

[33mcommit bddf82ce22febc31bb62960342b072aa8a0b4edd[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Feb 23 20:34:13 2026 +0000

    docs: changelog v1.7.0 - neron_web_voice

[33mcommit 944c74f05ed6e2e95d41d3ff79ccc3b2afca787e[m
Merge: 15be047 bcb1546
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Feb 23 20:29:58 2026 +0000

    Merge branch 'feature/neron-web-voice' into develop

[33mcommit bcb1546558ba6063c990693b09000e538d135688[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Feb 23 20:29:46 2026 +0000

    update start_neron.sh

[33mcommit f64630722beb6d8b33e5c64ddaca21f075b0061f[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Feb 23 20:16:31 2026 +0000

    ajout neron_web_voice -> Ports

[33mcommit 6f55c6a0bcea7941c76decf401853b2d6a5b0aa8[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Feb 23 18:57:16 2026 +0000

    feat: ajout du service neron_web_voice
    
    - Nouveau service Node.js avec interface vocale web
    - HTTPS via certificats montes en volume
    - Proxy STT et Core LLM integre
    - Reseaux Neron_Network et neron_internal
    - Port 8080

[33mcommit a1d32c4895e2d09522406e3174614ddc0e1f82d3[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Feb 23 18:05:35 2026 +0000

     Ajout du modules neron_web_voice

[33mcommit 15be04794dedbab651f4d2e3652d23d75aaf2d67[m
Merge: 8b0ed3b 9a56742
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Feb 23 07:16:48 2026 +0000

    Merge tag 'neron_stt' into develop
    
    neron_stt add Nerwork

[33mcommit 9a56742df2293192c78edfa9403a5503f895c2e1[m[33m ([m[1;33mtag: [m[1;33mneron_stt[m[33m)[m
Merge: 6683b44 fd648a0
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Feb 23 07:16:26 2026 +0000

    Merge branch 'hotfix/neron_stt'

[33mcommit fd648a03f8877ba7682d545f27fa758200ba5f16[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Feb 23 07:12:16 2026 +0000

    ajout Neron_Network au STT comme le Core

[33mcommit 8b0ed3b5a90a6a6851a5f80dc49561590171a6c7[m
Merge: f798e69 6683b44
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Feb 23 07:01:17 2026 +0000

    Merge tag 'bugfix' into develop
    
    bugfix

[33mcommit 6683b44eb9f1db87b9b9dc50944c1c21bc450990[m[33m ([m[1;33mtag: [m[1;33mbugfix[m[33m)[m
Merge: 69620fb b4f427f
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Feb 23 07:01:09 2026 +0000

    Merge branch 'hotfix/bugfix'

[33mcommit b4f427f8ef8666c641db466d75fe3030cbd76751[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Feb 23 07:00:42 2026 +0000

     fixbug ports sur neron_stt

[33mcommit f798e69ec3963899a58048ae895c6dd1c34dda5c[m
Merge: 8d6c589 69620fb
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Feb 23 06:57:40 2026 +0000

    Merge tag 'port-stt' into develop
    
    port-stt

[33mcommit 69620fbb5b8f20e0a0577d9a6626446bef382cab[m[33m ([m[1;33mtag: [m[1;33mport-stt[m[33m)[m
Merge: d65c99f 462ffe8
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Feb 23 06:57:29 2026 +0000

    Merge branch 'hotfix/port-stt'

[33mcommit 462ffe8f25e72ad5123662ddcd9650925a67d87b[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Feb 23 06:57:03 2026 +0000

    hotfix: exposition du port 8001 pour neron_stt
    
    - Ajout du mapping 0.0.0.0:8001->8001 pour rendre le service
      accessible depuis le réseau local

[33mcommit d65c99ff7c9737b9d110590bcd195d872f250b3c[m
Merge: 705b822 d6de4fe
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Feb 22 01:00:37 2026 +0000

    update

[33mcommit d6de4fe10c3a8f8abda8f1415408ccf5598436d1[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Feb 22 00:54:16 2026 +0000

     mise a jour de README.md / CHANGELOG.md / QUICKSTART.md / start_neron.sh

[33mcommit 705b822f5174cc1e3034acaa42343195c3bfa300[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Feb 22 00:43:42 2026 +0000

    docs: mise a jour documentation v1.6.0
    
    - README.md : architecture complete, services, API, performances
    - CHANGELOG.md : historique v1.0.0 -> v1.6.0
    - QUICKSTART.md : exemples /input/audio et /input/voice
    - start_neron.sh : v1.6.0, main, show_endpoints, fix guillemets

[33mcommit 8d6c589ea49610d3d51fbf18a71c334f1b9313f1[m[33m ([m[1;33mtag: [m[1;33mrm[m[33m)[m
Merge: 8c1b008 0da1c55
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 21 23:51:22 2026 +0000

    Merge branch 'feature/neron_tts' into develop

[33mcommit 0da1c55e518f9177b47f9d94ae2c8c10948524b4[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 21 23:50:07 2026 +0000

    test(tts): 9 tests tts_agent - 68 tests total
    
    - test_texte_vide_rejete
    - test_texte_espaces_rejete
    - test_synthese_succes
    - test_synthese_latency_presente
    - test_synthese_timeout
    - test_synthese_http_error
    - test_synthese_service_indisponible
    - test_check_connection_ok
    - test_check_connection_echec
    
    59 -> 68 tests

[33mcommit 669642bd5ea630391558d357539dc991b78801d1[m[33m ([m[1;33mtag: [m[1;33mv1.6.0[m[33m)[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 21 23:47:43 2026 +0000

    feat(tts): v1.6.0 - pipeline vocal complet STT+TTS
    
    - neron_tts service : pyttsx3, adapter pattern TTSEngine
    - tts_agent.py : client HTTP vers neron_tts:8003
    - POST /input/voice : audio -> STT -> LLM -> TTS -> audio WAV
    - global tts_agent corrige dans lifespan
    - pipeline vocal : HTTP 200, 825 bytes audio retourne

[33mcommit 8c1b0080298d9a8c4e37d3c288feaae92eccb6d7[m[33m ([m[1;33mtag: [m[1;33mv1.5.0[m[33m)[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 21 22:05:46 2026 +0000

    test(stt): 11 tests stt_agent - 59 tests total
    
    - test_format_wav_accepte
    - test_format_mp3_accepte
    - test_format_invalide_rejete
    - test_format_pdf_rejete
    - test_transcription_succes
    - test_transcription_metadata
    - test_transcription_timeout
    - test_transcription_http_error
    - test_transcription_service_indisponible
    - test_check_connection_ok
    - test_check_connection_echec
    
    48 -> 59 tests

[33mcommit 8cc66b660de29cd773bb31a23f6a97552dea2431[m
Merge: d6f0c68 fc57552
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 21 21:50:26 2026 +0000

    Merge branch 'feature/neron-stt' into develop

[33mcommit fc57552cf9a8a4e92617415fa0fb92f6864d4189[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 21 21:49:53 2026 +0000

    perf(stt): optimisation Docker + faster-whisper CPU-only
    
    - passage à faster-whisper int8 pour STT
    - limitation threads CPU (OMP_NUM_THREADS, MKL_NUM_THREADS)
    - multi-stage build pour image plus légère
    - versions fixées dans requirements.txt
    - préparation pour latence réduite et stabilité CPU-only

[33mcommit b5908f4be7b996e19fce76c3963f56840a850bae[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 21 21:26:50 2026 +0000

    perf(stt): faster-whisper int8 - latence -68%
    
    - openai-whisper remplace par faster-whisper==1.0.3
    - compute_type=int8 (CPU-optimise)
    - warmup au startup
    - limite taille audio (AUDIO_MAX_SIZE_MB=10)
    - WHISPER_LANGUAGE=fr force
    - STT : 24s -> 7.8s (-68%)
    - version neron_stt 1.0.0 -> 1.1.0

[33mcommit 1489ebf598c005f6ab12d49a46caa4d0fbb73253[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 21 21:01:03 2026 +0000

    feat(stt): v1.5.0 - pipeline audio complet operationnel
    
    - neron_stt: Whisper base, langue configurable (WHISPER_LANGUAGE=fr)
    - neron_stt: modele pre-telecharge au build (pas besoin internet au runtime)
    - neron_stt: gestion transcription vide dans neron_core
    - stt_agent: correction AgentResult (source manquant)
    - docker-compose: neron_stt actif sur neron_internal
    - .env: NERON_STT_URL=http://neron_stt:8001, WHISPER_LANGUAGE=fr
    - Pipeline: audio -> STT -> intent -> LLM -> CoreResponse
    - 48 tests passes

[33mcommit 7e6cdd0f89b98f1019d2a33cc6b4c55be789d46e[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 21 18:40:38 2026 +0000

    feat(stt): ajout service neron_stt v1.0.0
    
    - modules/neron_stt/app.py : FastAPI + Whisper, endpoint /transcribe
    - modules/neron_stt/Dockerfile : python:3.11-slim + ffmpeg + user non-root
    - modules/neron_stt/requirements.txt : whisper, fastapi, uvicorn
    - agents/stt_agent.py : client HTTP vers neron_stt (AgentResult)
    - app.py : endpoint POST /input/audio (audio -> STT -> pipeline texte)
    - app.py : stt_agent instancie au startup
    - docker-compose.yaml : neron_stt active sur neron_internal
    - neron_core/requirements.txt : ajout python-multipart
    - 48 tests passes

[33mcommit d6f0c68ec0451b25af8399cd5c4cefafa9bcf18d[m
Merge: 5d063c5 04444ae
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 21 17:14:05 2026 +0000

    Merge tag 'neron_memory-fix' into develop
    
    neron_memory-fix

[33mcommit 04444ae93c533b84fd3753d89212c52837f5f479[m[33m ([m[1;33mtag: [m[1;33mneron_memory-fix[m[33m)[m
Merge: e495cf0 512b9d6
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 21 17:13:39 2026 +0000

    Merge branch 'hotfix/neron_memory-fix'

[33mcommit 512b9d607f0dd0f5c02cbdb6f2aa23f3cd069d32[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 21 17:13:16 2026 +0000

    Hotfix: corrige version sqlite-utils pour neron_memory

[33mcommit 5d063c5aaa5552774b84deed385928f49c3cec8a[m
Merge: 667ee79 e495cf0
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 21 16:46:00 2026 +0000

    Merge tag 'debug' into develop
    
    debug

[33mcommit e495cf05a79383172eee56ae8f4093c391b0083f[m[33m ([m[1;33mtag: [m[1;33mdebug[m[33m)[m
Merge: 6c4a8fa 92e9f21
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 21 16:45:19 2026 +0000

    Merge branch 'hotfix/debug'

[33mcommit 92e9f219e23c2600c6ddd9b1b67458a76f535f82[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 21 16:44:57 2026 +0000

    retrait de fichier test

[33mcommit 667ee7967618ba6cf8ca43afae3908d3c01377df[m
Merge: 7e7a07f 6c4a8fa
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 21 16:43:17 2026 +0000

    Merge tag 'v1.4.1' into develop
    
    v1.4.1

[33mcommit 6c4a8fae45ced9fddf63ff86b2fefa0eece42324[m[33m ([m[1;33mtag: [m[1;33mv1.4.1[m[33m)[m
Merge: 5a28ecb bcc68b6
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 21 16:43:06 2026 +0000

    Merge branch 'release/v1.4.1'

[33mcommit bcc68b64e3afb938dc67e4e767e13aa6021686c7[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 21 16:42:43 2026 +0000

     mise a jour de CHANGELOG.md

[33mcommit 7e7a07f2b08d38b5cf553baf18ac3993c05a07bf[m
Merge: 66aac57 8a7b978
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 21 16:36:08 2026 +0000

    Merge branch 'feature/neron_optimisation' into develop

[33mcommit 8a7b978da1d72290029b7866ae709af4d0ac9c11[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 21 16:35:48 2026 +0000

    retrait modules non developpe

[33mcommit 6d8c990d4d6feb6d31a3e71c787582a4e1d0dbb2[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 21 16:32:42 2026 +0000

    Optimisation Dockerfile neron_web : multi-stage, pip cache supprimé, base slim, requirements clean

[33mcommit 6a23198ce97b28b77d2cdc65055de852b02c75cf[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 21 16:21:15 2026 +0000

    Optimisation Dockerfile neron_memory : multi-stage, pip cache supprimé, base slim, requirements clean

[33mcommit 24aa0b58d74cb9210127423758097f337cc4ee6c[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 21 16:17:07 2026 +0000

    Optimisation Dockerfile neron_llm : multi-stage, nettoyage pip, base slim
    Netoyage doublons requirements

[33mcommit 66aac577039a65d1de9c9f6398ee56317bd39993[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 21 16:04:45 2026 +0000

    Optimisation Dockerfile neron_llm : multi-stage, suppression cache et outils build

[33mcommit ebd1b27c1060e23839bb8ed0ee293feb70372474[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 21 15:04:35 2026 +0000

    neron_core: optimisation image Docker (réduction 4.6GB -> 336MB, nettoyage deps et layers)

[33mcommit 5a28ecbbca0d81f704e69b285aa400a06aa7fb29[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Feb 20 14:30:08 2026 +0000

    modif start_neron

[33mcommit 3e8aa11093239fe898ca7bae470878d3bb3b7a70[m
Merge: 29cf2f8 dd79e6f
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Feb 20 08:37:28 2026 +0000

    Merge tag 'add_start_script' into develop
    
    add script

[33mcommit dd79e6fb992adb58a6c5fbf769a2761250ff4f5d[m[33m ([m[1;33mtag: [m[1;33madd_start_script[m[33m)[m
Merge: d659ff1 819f8db
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Feb 20 08:37:12 2026 +0000

    Merge branch 'hotfix/add_start_script'

[33mcommit 819f8db9a6ad32ad4a99878d91cf0ed02c0b737a[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Feb 20 08:37:12 2026 +0000

    hotfix: ajout nettoyage et rebuild dans start_neron.sh

[33mcommit 29cf2f875e9721a97efa9c33ff06a278fcc6a24c[m
Merge: 74046e3 d659ff1
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Feb 20 08:29:55 2026 +0000

    Merge tag 'v1.4.0' into develop
    
    v1.4.0

[33mcommit d659ff17ed191ff72433bc7e55e4f3af51ca1215[m[33m ([m[1;33mtag: [m[1;33mv1.4.0[m[33m)[m
Merge: ae1fe0d 6ce3870
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Feb 20 08:29:45 2026 +0000

    Merge branch 'release/v1.4.0'

[33mcommit 6ce3870fd4f0a4a02543a418106bb8aaad5e62c0[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Feb 20 08:29:32 2026 +0000

    fix(config): NERON_MEMORY_URL corrige en nom Docker (neron_memory:8002)
    
    - Remplace http://192.168.1.130:8002 par http://neron_memory:8002
    - Memory store fonctionne via neron_internal
    - Plus de memory_store_failed dans les logs

[33mcommit 74046e329e9f8f772de2afd7243c2e935ae5e215[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Feb 20 08:08:19 2026 +0000

    feat(metrics): observabilite enrichie v1.4.0
    
    - neron_uptime_seconds : duree depuis demarrage
    - neron_requests_total : compteur total requetes
    - neron_requests_in_flight : requetes en cours (gauge)
    - neron_execution_time_avg_ms : temps moyen orchestration global
    - record_request_start/end avec bloc finally (fiable meme en cas d erreur)
    - latencies stockees par agent (dict) au lieu de liste plate
    - 48 tests passes

[33mcommit d4cf1f119debca68a6de0089c57b1cb345e2564a[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Feb 20 07:21:20 2026 +0000

    feat(core): standardisation des reponses API v1.4.0
    
    - CoreResponse enrichie : agent, timestamp UTC, execution_time_ms, model, error
    - VERSION constante dans app.py (plus de hardcoding)
    - utc_now_iso() helper pour timestamp uniforme
    - execution_time_ms : temps total orchestration (vs latency_ms agent interne)
    - 8 nouveaux tests test_core_response.py (patch LLMAgent/WebAgent/Router)
    - Total : 48 tests passes.

[33mcommit 9c54a4c568a1d501a27405a6c99c4e1d6a21e692[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 19 22:40:53 2026 +0000

    feat(infra): isolation réseau Docker v1.4.0
    
    - Ajout réseau neron_internal (bridge internal: true)
    - Suppression ports exposés : neron_llm, neron_ollama, neron_memory, neron_searxng
    - neron_core seul point d'entrée sur 0.0.0.0:8000
    - neron_web maintenu sur 7860 (accès direct navigateur)
    - neron_stt commenté (non implémenté)
    - neron_core et neron_web sur deux réseaux (Neron_Network + neron_internal)

[33mcommit dd4a67265eb2c1ff5633d969a49282d2cc90e21e[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 19 22:15:04 2026 +0000

    chore: ignore local config backup

[33mcommit 37b93304b03ed970c4722c46d748da647c2de3b4[m
Merge: 8436993 ae1fe0d
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 19 22:13:37 2026 +0000

    Merge tag 'v1.3.3' into develop
    
    v1.3.3

[33mcommit ae1fe0d84e7a2dc0da20de98e97c0e278e407eeb[m[33m ([m[1;33mtag: [m[1;33mv1.3.3[m[33m)[m
Merge: 128c460 8436993
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 19 22:13:24 2026 +0000

    Merge branch 'release/v1.3.3'

[33mcommit 8436993435b579a7809aee9db38d825642ccea2d[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 19 22:00:45 2026 +0000

    fix(time): accents francais dans human() - fevrier -> février, aout -> août

[33mcommit 80a805a012a5d58510e5de3438b02c476943f109[m
Merge: d2ef5ca aa8e4c5
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 19 21:37:17 2026 +0000

    Merge branch 'feature/neron_core' into develop

[33mcommit aa8e4c58ddccc391480ec71c2b065150800b67d8[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 19 21:37:09 2026 +0000

    mise a jour CHANGELOG

[33mcommit 459bea85f2bba6f22d6b3150abe7c004b49f96d4[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 19 21:22:02 2026 +0000

    fix(core): LLMAgent lit OLLAMA_MODEL depuis .env et le transmet a neron_llm
    
    - Ajout variable OLLAMA_MODEL dans llm_agent.py
    - Modele transmis dans chaque requete POST /ask
    - Metadata retourne le modele effectivement utilise
    - Changement de modele : modifier OLLAMA_MODEL dans .env uniquement

[33mcommit d2ef5caf4ad5bd3ce0184855f82196850186797d[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 19 20:48:07 2026 +0000

    modifie numero version

[33mcommit 2bf0a6dae4be81b5c75e47977c2dca0cd7406b9c[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 19 20:37:12 2026 +0000

    feat(core): branchement TimeProvider dans le pipeline v1.3.3
    
    - Ajout handler _handle_time_query dans app.py
    - TimeProvider instancie au startup avec les autres agents
    - Intent TIME_QUERY repond sans passer par le LLM
    - Dockerfile : ajout COPY neron_time/ pour inclusion dans l'image
    - human() en francais sans dependance locale (dictionnaires integres)
    - Reponse testee : 'Il est jeudi 19 fevrier 2026 a 21h36.'
    - 40 tests passes, neron_core up

[33mcommit b17005cfbd9926f93b41931b617c396755878126[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 19 19:51:30 2026 +0000

    feat(core): ajout TimeProvider et intent TIME_QUERY v1.3.2
    
    - Ajout neron_time/time_provider.py (zoneinfo, sans dependance externe)
    - Methodes : now(), iso(), human(), date(), time(), timestamp()
    - Fuseau horaire configurable (defaut Europe/Paris)
    - Ajout Intent.TIME_QUERY dans intent_router.py
    - Patterns detectes : heure, date, quel jour, quel mois
    - 15 tests pytest pour TimeProvider (15/15 PASS)
    - 3 nouveaux tests TIME_QUERY dans test_router.py
    - Total : 40 tests passes
    
    Note : TIME_QUERY detecte mais pas encore branche dans app.py

[33mcommit d5027ac84034bbebca591bffd7e9bfeb5977bd94[m[33m ([m[1;33mtag: [m[1;33mv1.3.1[m[33m)[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Feb 19 10:08:21 2026 +0000

    feat(core): orchestrateur multi-agents v1.3.0/1.3.1
    
    - Ajout IntentRouter rules-based + LLM fallback
    - Ajout BaseAgent, LLMAgent, WebAgent
    - Ajout neron_searxng self-hosted
    - Corrections audit DevOps (securite, robustesse, metrics)
    - 22 tests pytest passes
    - CHANGELOG mis a jour

[33mcommit 4eb56144e202ecb3914904825f07ab1bd993884c[m
Merge: 686e920 e20d65a
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Wed Feb 18 21:45:29 2026 +0000

    Merge branch 'feature/neorn_core-v1.3.0' into develop

[33mcommit 686e920d1205f417e8f23eb33c616783c331ece2[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Wed Feb 18 21:36:34 2026 +0000

    Sauvegarde temporaire avant switch branch

[33mcommit 128c4603880a29f247299477b0d4b6e26b9d168e[m
Merge: cc64f80 e20d65a
Author: enabeteleazar <161418955+enabeteleazar@users.noreply.github.com>
Date:   Wed Feb 18 22:31:40 2026 +0100

    Merge pull request #3 from enabeteleazar/feature/neorn_core-v1.3.0
    
    Feature/neorn core v1.3.0

[33mcommit 984a8639e183f12c5fca30301ee3794f9ab891ec[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Wed Feb 18 21:20:49 2026 +0000

    update .gitignore

[33mcommit e20d65aab36b8c1d6792cb362fd5fac6c5883056[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Wed Feb 18 21:16:11 2026 +0000

    chore(neron_core): nettoyage __pycache__, orphelins et artefacts
    
    - Suppression de tous les __pycache__/ et .pyc
    - Suppression de config/settings.bak
    - Suppression du répertoire neron-core/ (artefact)
    - Suppression des dossiers sans .py source (core/, llm/, memory/, tools/)
    - Mise à jour Dockerfile pour copier tous les modules nécessaires

[33mcommit 7cc689e8b10d8175a70c2bee38bda8349b7510cf[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Wed Feb 18 20:39:01 2026 +0000

    test(orchestrator): ajout suite de tests IntentRouter
    
    - 7 tests couvrant CONVERSATION, WEB_SEARCH, HA_ACTION
    - conftest.py pour résolution du PYTHONPATH
    - Tous les tests passent en 0.04s

[33mcommit 9c3233435cf97680a6c183e3e39633551622f13c[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Wed Feb 18 20:28:46 2026 +0000

    fix(neron_core): résolution des imports manquants et pipeline LLM
    
    - Ajout du package agents/ (LLMAgent, WebAgent, AgentResult, base_agent)
    - Ajout du package orchestrator/ (IntentRouter, Intent, IntentResult)
    - Mise à jour Dockerfile pour copier agents/ et orchestrator/
    - Correction NERON_LLM_URL dans docker-compose.yaml (neron_llm:5000)
    - Pipeline complet opérationnel : core→llm→ollama
    
    Closes: ModuleNotFoundError agents, orchestrator.intent_router
    Tested: POST /input/text retourne une réponse valide

[33mcommit f4962c7dc9f739817c0e764549a007815e72b696[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Wed Feb 18 19:18:35 2026 +0000

    feat(neron_core): initial import v1.3.0 orchestrator
    
    - Ajout des nouveaux agents : base_agent, llm_agent, web_agent
    - Ajout de l'orchestrator : router.py
    - Réécriture complète de app.py pour orchestrer les intents
    - Ajout du service neron_searxng (SearXNG self-hosted)
    - Mise à jour docker-compose et .env.example
    - Nettoyage du requirements.txt (suppression des dépendances inutiles)

[33mcommit 7d72f98a54dd8b6d3a876539372ca13959184a81[m
Merge: 76d3a20 cc64f80
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Feb 15 17:22:24 2026 +0000

    Merge tag 'v1.2.2' into develop
    
    V1.2.2

[33mcommit cc64f809920aa36b762345756e4f60f821f7d980[m[33m ([m[1;33mtag: [m[1;33mv1.2.2[m[33m)[m
Merge: ee7f1b3 76d3a20
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Feb 15 17:22:15 2026 +0000

    Merge branch 'release/v1.2.2'

[33mcommit 76d3a2014726c0b2bd4b742e3737293c62c00561[m
Merge: fbb50f5 2f60dd2
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Feb 15 17:21:31 2026 +0000

    Merge branch 'feature/documentation' into develop

[33mcommit 2f60dd2ef8ba9ca5e0f4f3ff2b0b5cbcf42c5002[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Feb 15 17:21:09 2026 +0000

     ajout version

[33mcommit 600c7b53f2110529a2d90a5409ec07923f1eacbe[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Feb 15 17:19:10 2026 +0000

     ajout Documentatipon

[33mcommit fbb50f51ed56ae40f608fab8efcfd0f03defcb8e[m
Merge: df26a67 ee7f1b3
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Feb 15 15:01:12 2026 +0000

    Merge tag 'docker-network' into develop
    
    v1.2.1

[33mcommit ee7f1b3163935791b00ce6ed6b72ba6f9569455f[m[33m ([m[1;33mtag: [m[1;33mdocker-network[m[33m)[m
Merge: aedee9f 3450331
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Feb 15 15:01:05 2026 +0000

    Merge branch 'hotfix/docker-network'

[33mcommit 3450331fdfbb9718238d2bd20a30fac0e84c4dcc[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Feb 15 15:00:32 2026 +0000

    Add external networks Neron_Network and Homebox_Network for all Néron modules

[33mcommit df26a67fd38de6940e66dc2e648924c4b9752b54[m
Merge: 5fa052e aedee9f
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Feb 15 10:47:49 2026 +0000

    Merge tag 'v1.2.1' into develop
    
    v1.2.1

[33mcommit aedee9f719a7b203cf595f23f766fa1ecb40d80f[m[33m ([m[1;33mtag: [m[1;33mv1.2.1[m[33m)[m
Merge: c64c085 b2147f2
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Feb 15 10:47:42 2026 +0000

    Merge branch 'release/v1.2.1'

[33mcommit b2147f21e059b4e7d9e7762d4d4e030a5e16f129[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Feb 15 10:47:19 2026 +0000

    retrait fichier backup

[33mcommit 5fa052ee4a3d1cc14d81cd1fe8fafba68ae40612[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Feb 15 10:44:38 2026 +0000

    debug arborescence

[33mcommit 0d1e0aa63cff87e79171d6175a2812accec9425b[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 14 23:18:40 2026 +0000

    netoyage code

[33mcommit c64c0851056ebb9af78f9b3c9241cfcbd4827e86[m
Merge: 9240329 905cf85
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 14 23:08:57 2026 +0000

    Merge tag 'v1.2.0' into develop
    
    v1.2.0

[33mcommit 905cf85bd30aea62785129614b2ea8b221740b3e[m[33m ([m[1;33mtag: [m[1;33mv1.2.0[m[33m)[m
Merge: c03d00a 9240329
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 14 23:06:54 2026 +0000

    debug ...

[33mcommit 924032926296004f4f2be6eee8c92e766e3e537b[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 14 22:39:23 2026 +0000

    debug neron_web

[33mcommit 9375a2471dc4aa906811a5560ca6798e0d28f2d4[m
Merge: 9ed79e7 257a8ab
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 14 18:47:44 2026 +0000

    Merge branch 'feature/struct-neron' into develop

[33mcommit 257a8abd9cf15cc45d48ea857ef364f38cf80a5c[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 14 18:47:11 2026 +0000

    Fin de retructuration Neron_AI

[33mcommit c3cba111b845744e23214d2a2b4229aab942f5cb[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 14 18:26:09 2026 +0000

    neron_web opérationnel

[33mcommit 70786bbc9354bf7b2d563b1fe8a56174a007af56[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Feb 14 17:46:34 2026 +0000

    neron_llm & neron_ollama operationnel

[33mcommit d8bda28a1e28c9c56126f649d501d0113e3db2a7[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Feb 13 22:39:08 2026 +0000

    modif du chemin pour .env

[33mcommit c03d00a2156f8ce727b471c24e76ed7824c539cb[m[33m ([m[1;33mtag: [m[1;33m0.2.0[m[33m)[m
Merge: 1a63904 c65167a
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Wed Jan 28 07:09:47 2026 +0000

    Merge branch 'release/0.2.0'

[33mcommit c65167ad14712583fca7a9fd7c0b685e165cd502[m
Merge: 1a63904 bf9994b
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Wed Jan 28 07:04:16 2026 +0000

    Merge branch 'feature/neron-core' into develop

[33mcommit bf9994b054049029462dce6023d4dbd1b3f81c9d[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Wed Jan 28 07:03:47 2026 +0000

    feat: Néron Modelfile - Personnalité JARVIS intégrée
    
    ✅ PERSONNALITÉ NÉRON
    - Modèle custom basé sur qwen2.5:0.5b
    - System prompt JARVIS-like intégré
    - Ton décontracté mais respectueux
    - Style: phrases courtes, tutoiement naturel
    - Comportement proactif et bienveillant
    
    🔧 IMPLÉMENTATION
    - Modelfile créé dans neron-llm/
    - Prompt stocké dans system-prompt.txt
    - Modèle compilé: neron-custom
    - Parameters: temperature 0.7, top_p 0.9, top_k 40
    
    📊 RÉSULTAT
    - Réponses cohérentes avec la personnalité
    - Ton distinctif vs modèle générique
    - Identité claire: 'Je suis Néron, assistant IA...'
    - Temps de réponse: ~15-20s (qwen2.5:0.5b)
    
    🎯 UPGRADE PATH
    - Modelfile réutilisable pour n'importe quel modèle de base
    - Bascule simple: FROM llama3.3:70b
    - Personnalité préservée lors des upgrades
    
    🗂️ FICHIERS
    - neron-llm/Modelfile
    - neron-llm/system-prompt.txt
    - OLLAMA_MODEL=neron-custom dans .env
    
    ✨ Néron v0.2 a maintenant une vraie personnalité !

[33mcommit 853671896b38353dc723969415d42d1c932d9b7e[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Tue Jan 27 22:53:11 2026 +0000

    feat: Néron v0.2 - Architecture complète Multi-Interface
    
    ✅ CORE
    - Orchestrateur async (FastAPI + httpx)
    - Pipeline: text → LLM → memory
    - Gestion erreurs robuste + timeouts configurables
    - Healthchecks Docker sur tous les services
    
    ✅ LLM
    - Ollama qwen2.5:0.5b (optimisé vitesse/qualité)
    - Support llama3.2:1b en fallback
    - Timeout LLM: 120s
    
    ✅ MEMORY
    - SQLite persistant sur /mnt/usb-storage/Docker/volumes/
    - API complète: /store, /retrieve, /search, /stats
    - Context manager thread-safe
    - Survit aux rebuilds (volume nommé)
    
    ✅ STT
    - Whisper base (CPU)
    - Formats: wav, mp3, m4a, ogg, flac
    
    ✅ WEB (Gradio)
    - Interface chat responsive
    - Exemples intégrés
    - Port: 7860
    
    ✅ TELEGRAM BOT
    - Commandes: /start, /stats, /help
    - Réponses en temps réel
    - Indicateur 'typing'
    - Logs structurés
    
    🏗️ ARCHITECTURE
    - Docker Compose multi-services
    - Réseau: Neron_Network
    - Variables .env centralisées
    - Healthchecks automatiques
    - Restart policies
    
    📊 TESTS VALIDÉS
    - Pipeline complet: OK
    - Persistance mémoire: OK
    - Gradio: OK
    - Telegram: OK
    - Stats API: OK
    
    🔧 CONFIG
    - Modèle: qwen2.5:0.5b
    - Timeout LLM: 120s
    - Données: USB storage
    - Logs: structurés (INFO level)
    
    📦 DEPLOY
    docker compose up -d --build

[33mcommit 9ed79e7b58acb7318c037d6d7adadc81764290fd[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Tue Jan 27 15:58:37 2026 +0000

    feat: Néron v0.2 - Système complet et validé
    
    ✅ Architecture modulaire Docker
    ✅ Core: Orchestrateur async (httpx)
    ✅ LLM: Ollama qwen2.5:0.5b (optimisé vitesse)
    ✅ Memory: SQLite persistant + API complète
    ✅ STT: Whisper base
    ✅ Web: Interface Gradio fonctionnelle
    
    🧪 Tests validés:
    - Pipeline text → LLM → memory : OK
    - Persistance après rebuild : OK
    - API /retrieve, /search, /stats : OK
    - Interface Gradio responsive : OK
    
    📊 Stats:
    - Temps réponse LLM: ~5-15s
    - Mémoire stockée sur: /mnt/usb-storage/Docker/volumes/
    - Port Gradio: 7860

[33mcommit c87c324a8eaea0aeb732a56aafa2f97ef40b4283[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Tue Jan 27 07:12:32 2026 +0000

    feat: Néron Memory - API complète
    
    ✅ Endpoints:
    - GET /retrieve - Récupération historique
    - GET /search - Recherche par mots-clés
    - GET /stats - Statistiques
    - DELETE /clear - Nettoyage
    
    ✅ Tests validés:
    - Stockage OK
    - Récupération OK
    - Stats OK
    
    🎉 Système complet et fonctionnel

[33mcommit c9d4a232d54371506329f0f7a3d140e220d53948[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Tue Jan 27 06:21:19 2026 +0000

    feat: Néron v0.2 - Core fonctionnel avec LLM Ollama
    
    ✅ Fonctionnalités:
    - neron-core: Orchestrateur avec pipeline text → LLM → memory
    - neron-llm: Intégration Ollama (llama3.2:1b)
    - neron-stt: Service Whisper pour transcription audio
    - neron-memory: Stockage SQLite des conversations
    - Docker Compose: Architecture microservices complète
    - Healthchecks: Surveillance des services
    
    🔧 Corrections:
    - Fix: Async avec httpx au lieu de requests
    - Fix: Format API Ollama correct
    - Fix: Gestion d'erreurs HTTP robuste
    - Fix: Timeouts configurables
    - Fix: Logging structuré

[33mcommit 1a63904ae73af29a20c49a14b9c0923d9bfe744c[m
Merge: 45ccad7 03544fb
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Jan 25 21:10:01 2026 +0000

    Merge branch 'feature/Neron-v0.2' into develop

[33mcommit 45ccad7641ddabd30b094a6510ab51aa22a0c091[m
Merge: e759966 db15a9d
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Jan 25 14:11:04 2026 +0000

    chore: resolve .gitignore conflicts and clean runtime exclusions

[33mcommit e759966e8714e69317971c6787220a00c54efb29[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Jan 24 16:54:25 2026 +0000

    update

[33mcommit 7255bfd753321da10628bb3ac64fbd1020606a79[m
Merge: 0b39bc5 a42e7e3
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Jan 24 16:33:15 2026 +0000

    Merge remote-tracking branch 'origin/feature/pythonista' into feature/pythonista

[33mcommit 0b39bc54110370b4b49722b480414c0e5f3cffb2[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Jan 24 12:52:07 2026 +0000

     ajout de pythonista

[33mcommit 03544fb979661bc7c61a1a556f93c9ffc8b74ec3[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Jan 24 12:51:16 2026 +0000

     ajout de pythonista

[33mcommit 96331c6e3e433cebcedf4c15107c70883e45b90d[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Jan 23 14:49:26 2026 +0000

    Harmonisation des Dockerfile

[33mcommit db15a9dbc1c9370d7c716e61218991f7f181244b[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Jan 23 11:33:44 2026 +0000

    feat: stabilisation complète de la stack Néron v0.1
    
    - Correction des erreurs de démarrage FastAPI (indentation, dépendances)
    - Mise en place correcte des environnements virtuels Python (venv)
    - Ajout de curl dans les images Docker pour les healthchecks
    - Correction des endpoints /health (core, stt, memory)
    - Désactivation temporaire du healthcheck de neron-llm (Ollama fonctionnel)
    - Correction des dépendances Docker et du réseau neron-network
    - Démarrage et fonctionnement validés de tous les services Néron v0.1
    
    Statut : tous les services sont opérationnels

[33mcommit 7fa50ae357575f41754872485312bd060a5c83e3[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Jan 22 23:30:43 2026 +0000

     ajout de Neron v0.1

[33mcommit a42e7e3ba6c3cf92093c0bdf805563eb342b139f[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Jan 17 23:21:57 2026 +0100

    Ajout Pyhtonista

[33mcommit 669d1c731f25289638cb62c03be5e71326c335f2[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Jan 17 19:10:28 2026 +0100

    Update Files

[33mcommit e6609ee24bfb1eedab79bc6fd35f87da7972eb4a[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Wed Jan 14 21:04:07 2026 +0000

    reparation Dashboard

[33mcommit 5720fd67d7f3d79cdd709e625a11d1fad5ab2e0f[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Wed Jan 14 00:11:57 2026 +0000

    fix: Correct permissions and ensure all Homebox services start properly
    
    - Created and set correct UID/GID and permissions for all service volumes:
      - Grafana (472:472)
      - Home Assistant (1000:1000)
      - Node-RED (1000:1000)
      - Prometheus (65534:65534)
      - N8N (1000:1000)
    - Added minimal Prometheus configuration file (prometheus.yml) to allow proper startup
    - Updated docker-compose volumes to ensure correct paths and ownership
    - Verified that all services (Grafana, Home Assistant, Node-RED, Prometheus, N8N) start without reboot loops
    - Included a bash script (homebox_fix_restart.sh) to automate folder creation, permission fixes, and service relaunch

[33mcommit 0f9eb565013bad06fb3ddc7f79c5d038d3ba2f2e[m
Merge: 5c6a3a7 a618609
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Tue Jan 13 22:39:37 2026 +0000

    Merge branch 'feature/docker-compose' into develop

[33mcommit a61860968d5355b042a80a2536856e3eabd53fb9[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Tue Jan 13 22:22:37 2026 +0000

    feat(Portainer): Update compose.yaml

[33mcommit 5c6a3a7f53fe399d49a3f591b4afa571258f8bad[m
Author: enabeteleazar <161418955+enabeteleazar@users.noreply.github.com>
Date:   Tue Jan 13 08:58:04 2026 +0100

    Update docker-compose.yaml (n8n)

[33mcommit 836b814928e1e346faf8edd29ee04f5077ea91ad[m
Author: enabeteleazar <161418955+enabeteleazar@users.noreply.github.com>
Date:   Tue Jan 13 08:57:07 2026 +0100

    Update docker-compose.yaml (llama+Telegram)

[33mcommit fd77d386f3f3b595981b4ebe4831ce955e883d0b[m
Author: enabeteleazar <161418955+enabeteleazar@users.noreply.github.com>
Date:   Tue Jan 13 08:55:37 2026 +0100

    Update docker-compose.yaml (Node-Red)

[33mcommit 822e18c28ae671febf4d415268fbfe3f4998c147[m
Author: enabeteleazar <161418955+enabeteleazar@users.noreply.github.com>
Date:   Tue Jan 13 08:54:53 2026 +0100

    Update docker-compose.yaml (HomeAssistant)

[33mcommit 25051a07db3c09af006158d45464711d2a9ab0ad[m
Author: enabeteleazar <161418955+enabeteleazar@users.noreply.github.com>
Date:   Tue Jan 13 08:53:37 2026 +0100

    Update docker-compose.yaml (Grafana)

[33mcommit 83b6869941da2c72c045a67f42502f1be6fa7ea9[m
Author: enabeteleazar <161418955+enabeteleazar@users.noreply.github.com>
Date:   Tue Jan 13 08:52:41 2026 +0100

    Update docker-compose.yaml (Dashboard)

[33mcommit f5152589e439ed67fc47eed75f5e0f238a9b7c6a[m
Author: enabeteleazar <161418955+enabeteleazar@users.noreply.github.com>
Date:   Tue Jan 13 08:51:47 2026 +0100

    Update docker-compose.yaml (Cadvisor)

[33mcommit 8b9b32f38354699d7bd794894ad5054299ba04c7[m
Author: enabeteleazar <161418955+enabeteleazar@users.noreply.github.com>
Date:   Tue Jan 13 08:50:53 2026 +0100

    Update docker-compose.yaml (Beszel)

[33mcommit 57d1c609044e277474611baf58827d02189eb918[m
Author: enabeteleazar <161418955+enabeteleazar@users.noreply.github.com>
Date:   Tue Jan 13 08:50:03 2026 +0100

    Update docker-compose.yaml

[33mcommit 67f5c43003ae413688a925b8937a1f85d241e111[m
Author: enabeteleazar <161418955+enabeteleazar@users.noreply.github.com>
Date:   Tue Jan 13 08:49:13 2026 +0100

    Update docker-compose.yaml

[33mcommit faf188f6de4cb143b4fb0889e1af726ccdcdec65[m
Author: enabeteleazar <161418955+enabeteleazar@users.noreply.github.com>
Date:   Tue Jan 13 08:48:59 2026 +0100

    Update docker-compose.yaml

[33mcommit 1632b3931b1e0fec50cfa8f4a5aa45813edb3ba5[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Jan 12 22:48:46 2026 +0000

    Suppression Data/ du suivi Git

[33mcommit c62f1736ecc5464f729affb63980b6868377b702[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Jan 12 22:45:17 2026 +0000

    Update Variable .env & Docker-compose

[33mcommit c3a8c3a10d06fcc0d3350d765bf618a39919d6c8[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Jan 12 21:36:01 2026 +0000

    creation de la structure complete

[33mcommit bdb9bbfa215849be3ea26965850956b3e3d5f85a[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Jan 12 21:07:04 2026 +0000

    recuperation de Dashboard v1.4

[33mcommit 28936c81a52fbb2f867533637db8d1783fdf697c[m
Merge: c331750 7f0bd77
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Jan 12 20:47:57 2026 +0000

    Restructuration du Projet

[33mcommit 945e52a6ac3d71a9956ca391dc435954da542a0c[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Jan 12 20:36:31 2026 +0000

    Restructuration du Projet

[33mcommit c331750c566943e1de92ca52b242905a2e82538b[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Jan 12 20:36:31 2026 +0000

    Restructuration du Projet

[33mcommit 7f0bd7704a407458fe995b3c38e13bb478eb86f6[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Jan 11 20:28:08 2026 +0000

    feat(dashboard):Refonte complète du Monitoring complet avec backend amélioré

[33mcommit 5688394fd9e45dd77b3021940d3350b44e264fed[m
Merge: 2801df7 3df09a4
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Jan 10 23:39:47 2026 +0000

    Merge tag '1.4' into develop
    
    Normalisation JSON Backend.

[33mcommit 3df09a4fa371049d9cb5e4e2cb47ea1fd62b95a9[m
Merge: 5b8e745 2801df7
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Jan 10 23:39:09 2026 +0000

    Merge branch 'release/1.4'

[33mcommit 2801df790530739511ae63b9545f18040c883130[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Tue Jan 6 22:40:05 2026 +0000

    feat(api): normalisation JSON Docker v1.4

[33mcommit 18f37c4881f52269e45908dd681bc417fc4f782d[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Tue Jan 6 22:25:53 2026 +0000

    feat(api): endpoint health v1.4 – état global système, docker et services

[33mcommit f924317a5540f16c2104ac82899a2c9a9664f747[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Tue Jan 6 19:26:36 2026 +0000

    feat(api) endpoint systeme.Update

[33mcommit 0554f265e344eaa4b7a19403b8b50519452110bf[m
Merge: 1ff0c49 cfa1e85
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Tue Jan 6 19:21:21 2026 +0000

    Merge branch 'feature/system-endpoints' into develop

[33mcommit cfa1e85b74bb7f2364a1bfdb80bd604ddbedf42e[m
Merge: a09e7ec 143ca67
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Tue Jan 6 19:09:17 2026 +0000

    Merge remote-tracking branch 'refs/remotes/origin/feature/system-endpoints' into feature/system-endpoints

[33mcommit 1ff0c494b7a164424dbd92a3665b4133c693226a[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Tue Jan 6 19:06:50 2026 +0000

    feat(api): endpoints système v1.4 – métriques CPU, RAM, Disk, Température, summary pour dashboard

[33mcommit 143ca67e1673f2d93a0c92a357ccc8376a5f9864[m
Author: enabeteleazar <161418955+enabeteleazar@users.noreply.github.com>
Date:   Tue Jan 6 08:16:20 2026 +0100

    feat(api): endpoints système v1.4 – métriques CPU, RAM, Disk, Température, summary pour dashboard

[33mcommit a09e7ec9868ac04b28245278ecda1d8a77e386da[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Jan 5 23:35:05 2026 +0000

    feat: ajout complet des endpoints Docker list/summary/start/stop pour v1.4 S1

[33mcommit 5b8e745be58aedc558e6863eeda5091feb9949fc[m
Merge: 9a779f0 07631a0
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Jan 4 21:51:30 2026 +0000

    Merge branch 'release/1.3.2'

[33mcommit 07631a0c88de623bb6c7bdd1b5cd871a48a2d297[m
Merge: 4662c24 4a03d77
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Jan 4 21:37:25 2026 +0000

    Merge branch 'feature/dashboard-ui-docker' into develop

[33mcommit 4a03d7791139aabb577e9e0f7858c7769f52cf76[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Jan 4 21:36:42 2026 +0000

    docker-compose Port

[33mcommit 6e884e0cb3b3b97c32f8c2b1a96ee55786f6be01[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Jan 4 21:35:10 2026 +0000

    Activation des boutons Start/Stop Docker dans le dashboard avec méthode POST
    - Les boutons React utilisent désormais fetch POST vers /api/docker/<id>/start et /stop
    - Correction du 405 Method Not Allowed lors des actions Docker
    - Rafraîchissement automatique de la liste des containers après action
    - Désactivation conditionnelle des boutons selon l’état du container

[33mcommit 6d27189a4db50361e0686225fd3f248f99f31bb3[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Jan 4 20:34:09 2026 +0000

    Docker API : correction du calcul d'uptime et ajout d'une valeur vide pour les containers arrêtés

[33mcommit 8c2e72ee87e83e5ead018c190db2ebc288ea6a32[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Jan 4 19:51:29 2026 +0000

    feat(ui): ajout d'une navbar pour la navigation du dashboard

[33mcommit 4662c24e68b89ee5a54002d5c4d120849c514a39[m
Merge: 0ed5897 9a779f0
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Jan 4 18:12:59 2026 +0000

    Merge tag '1.3.1' into develop
    
    release v 1.3.1

[33mcommit 9a779f07f4ce6da0bfcd6fb9841a47ee0222ce63[m
Merge: e68bb9a 1ff57c8
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Jan 4 18:12:29 2026 +0000

    Merge branch 'release/1.3.1'

[33mcommit 1ff57c8662847798b67dce35c710f7b9c6205e55[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Jan 4 18:11:12 2026 +0000

    Correction backend : ajout de PYTHONPATH pour résoudre ModuleNotFoundError sur 'api', ajustement Dockerfile pour uvicorn et dépendances Python. Backend fonctionne maintenant sous docker-compose.

[33mcommit 0ed5897c5f5e0e3123dd5c40e0386cf17bbe149a[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Jan 4 16:08:53 2026 +0000

    Correction et refactor du Dashboard
    
    - Affichage de la température CPU corrigé (utilisation de systemData.cpu.temperature)
    - Suppression du champ obsolète `temp` dans App.jsx
    - Refactor de setSystemData pour éviter l'écrasement de cpu
    - Nettoyage et sécurisation des valeurs nulles pour CPU, RAM et Disk
    - Maintien des logs console pour debug des appels API système, Docker et Health
    - Refresh toutes les 2 secondes conservé
    - Affichage automatique des nouveaux services Docker et Health

[33mcommit 04e969918362e21f3a8bbfe64197d207b3bdd04d[m
Merge: 82b1d3b ab7f2c3
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Jan 3 20:48:54 2026 +0000

    Merge branch 'feature/api-normalisation' into develop

[33mcommit ab7f2c3b9d296dd70e6f98e65c6825777d7cdd16[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Jan 3 18:51:35 2026 +0000

    ajout du endpoint /health avec controle complet des services
    - création de l'endpoint /health por vérifier l'état des services ...
    - vérification de Docker, CUPS, Home Assistant, Neron LLM et codiTV
    - Gestion robuste des erreurs et retour uniforme avec timestamp UTC

[33mcommit aee74250408fb9b55defc5dca51f359ce4da023f[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Jan 3 18:28:27 2026 +0000

    Ajout du endpoint Docker avec gestion robuuste des dates
    - Création de l'endpoint /docker pour lister les containers
    - Conversion automatiquedes champs datetime Docker -( Created, StartedAt, FinishedAt )
    - Gestion des valeurs absentes ou mal formatées pour eviter les erreurs

[33mcommit 439516147345e61bb34f4945675274fcb53143fb[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Jan 3 17:19:56 2026 +0000

    feat(api): Ajout du endpoint de metrique systeme normalisées;
    - Ajout de l'endpoint /api/system avec sortie JSONnormalisée
    - Exposition des métriques CPU,RAM, swap, disque, temperature et uptime
    - Garantie que toutes les valeurs sont  sérialisables en jSON

[33mcommit 7436d0acd94c95c186b6688bb951c5547f0f1121[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Jan 1 22:13:51 2026 +0000

    backend: état stable avant normalisation API

[33mcommit ea93e1da10aefff0e71339ca4d1127e14eb4e727[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Jan 1 20:25:51 2026 +0000

    chore(dashboard) correction fetch API et état système"

[33mcommit 9281d6b04f96e1d86f681287ab4c0b89edc0beec[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Jan 1 18:10:06 2026 +0000

    chore(dashboard)reecriture du return()

[33mcommit 82b1d3b97b1df2fbc28b2e090d468dd286e6f65c[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Dec 21 00:28:55 2025 +0000

    chore(dashboard): Harmonisation du design du dashboard.

[33mcommit 9c404b778a3505f3021b0648bd536c314a57a8a2[m
Merge: 131df3c 4c805e9
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Dec 20 22:05:39 2025 +0000

    Merge branch 'feature/dashboard' into develop

[33mcommit 4c805e9f68db8978e4cf113a1c569e744b63bb20[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Dec 20 22:05:09 2025 +0000

    fix(dashboard):securisation des composants services du dashboard

[33mcommit 66e52673c053a042c867e1f40cd046b596075a07[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Dec 20 21:21:56 2025 +0000

    fix(dashboard): Securisation du rendu React et prevention des ecrans blanc.

[33mcommit 9f55f9fc676d569a5199b2d4dba3ea3ac662cb5f[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Dec 20 20:45:49 2025 +0000

    chore(dashboard - front) modif package-lock.json

[33mcommit de79a267c7838962dee5125a8e90404f9afbf030[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Dec 20 19:01:40 2025 +0000

    chore(dashboard - Front): modification du code

[33mcommit 4ddae83915d9ba3e09d1f1858765e1cb2a19d50d[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Dec 20 18:01:35 2025 +0000

    chore(frontend): mise en place de l'arborescence

[33mcommit 131df3cb8fff3a699d92a657d43e3e5ac25f7142[m
Merge: a8d50ee e68bb9a
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Dec 20 10:07:31 2025 +0000

    Merge tag '1.3.0' into develop
    
    v1.3.0 - add monitoring.

[33mcommit e68bb9a7c353715110162a4e1360885aa258c907[m
Merge: 2936293 ac01746
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Dec 20 10:07:10 2025 +0000

    Merge branch 'release/1.3.0'

[33mcommit ac01746cb867adc764ace7f6ff69f3d11d1ce56d[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Dec 20 10:03:43 2025 +0000

    release finish v1.3.0

[33mcommit 3e350f7f4d28bf805a5f5915ad7b4a73c43e9db8[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Dec 20 10:01:20 2025 +0000

    (file): Ajout de README

[33mcommit a8d50eedfe6d7b64e11ca5973910419d61f053aa[m
Merge: 8f2cf92 e9c1693
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Dec 20 09:47:59 2025 +0000

    Merge branch 'feature/1.3.0' into develop

[33mcommit e9c16933d658c43e971c0df5469f5b6efe3496b8[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Dec 20 09:47:30 2025 +0000

    installation de Prometheus & Cadvisor

[33mcommit b417a1029c7fe072725badf91831d4feb8f9686b[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Dec 20 09:35:37 2025 +0000

    chore(docker compose): modification d'emplacement du volume data

[33mcommit f770283cac26cf65706e7db5b2a8c4816e64928e[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Dec 19 15:53:42 2025 +0000

    chore(monitoring) ajout du systeme de monitoring

[33mcommit 8f2cf9262dad6aac6ed5001b38d033022e3675c7[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Dec 19 15:24:37 2025 +0000

    chore(venv) delete folder venv

[33mcommit 2936293c8dc944833944ab6749e84969f740a8bc[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Dec 19 15:05:18 2025 +0000

    hotfix

[33mcommit c1104fde07649ea941b10034544a6564915b5c9b[m
Merge: 9aa1df4 8291239
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Dec 19 14:32:31 2025 +0000

    Merge tag '1.2.2' into develop
    
    Fix.env variable et emplacement.

[33mcommit 82912391295362cb65d0af5717e3ad6039f8d1e0[m
Merge: 2a5387e c06a195
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Dec 19 14:32:01 2025 +0000

    Merge branch 'hotfix/1.2.2'

[33mcommit c06a195148e1386cacf1f05dcbb44910d8b25eef[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Dec 19 14:31:50 2025 +0000

    hotfix(1.2.1): Fix .env variable error

[33mcommit 9aa1df4ffdbe3583fb500fe1c065b023211cdf62[m
Merge: 6ba8012 2a5387e
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Dec 19 14:12:23 2025 +0000

    Merge tag '1.2.1' into develop
    
    v1.2.1

[33mcommit 2a5387e1e708753bcd3b7fbfc3aec4680afb47e5[m
Merge: 7bf9586 5dacf5c
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Dec 19 14:12:07 2025 +0000

    Merge branch 'hotfix/1.2.1'

[33mcommit 5dacf5ca763c120c20b96ac4ced8e8669ea292b6[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Dec 19 14:11:42 2025 +0000

    hotfix(1.2.1): Fix HomeAssistant Configuration

[33mcommit 7bf9586099d71aeb4120a7526632afb7aa9398f1[m
Merge: 3f9f236 63d1749
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Fri Dec 19 14:04:03 2025 +0000

    Remove .env fron tracking

[33mcommit 6ba801275529ac9941ff59ea2702d8a9acf5aefa[m
Merge: 7b4b43c 3f9f236
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Dec 18 23:48:20 2025 +0000

    Merge tag '1.2.0' into develop
    
    Deploiement de 1.2.0

[33mcommit 3f9f236eab2033e33b35e1d5fc6ff518140de116[m
Merge: 007f26c c60a99b
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Dec 18 23:47:27 2025 +0000

    clear

[33mcommit c60a99ba56cb5d02a756602b624a4507e23b5279[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Dec 18 23:45:04 2025 +0000

    chore(Release) Fin de preparation au deploiement

[33mcommit e8e8eca866fa574ea860b4f177bf19065e373d7b[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Dec 18 23:31:09 2025 +0000

    chore(.env): update variable

[33mcommit d9e425faef38c99c77c14d88017ab5e601d48525[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Dec 18 23:08:57 2025 +0000

    chore(release): préparation v1.2.0 pour Prod

[33mcommit 7b4b43c182e9d630ae86b47e0f55e1062d2f7252[m
Merge: 6c0bf23 4d3151c
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Dec 18 23:06:22 2025 +0000

    Merge branch 'feature/update-docker-env' into develop

[33mcommit 4d3151c424295e0c5e5c838caac51bca47ba55d8[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Dec 18 23:06:01 2025 +0000

    deplacement des service en cours de dev

[33mcommit 72bd7d68732c57195fe42960d8f0de4d06fa0190[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Dec 18 23:04:48 2025 +0000

    chore(llama.docker-compose): update

[33mcommit dd65d1b502bda60e3783ac6c977993b1c422dd21[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Dec 18 23:03:54 2025 +0000

    chore(llama.docker-compose): update

[33mcommit 462c139b33c677c3481918094acd4710258ebaf8[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Dec 18 23:01:33 2025 +0000

    chore(dashboard.docker-compose): update

[33mcommit 88c889cb9e364f7aace149d1ead264f6305335c0[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Dec 18 22:55:00 2025 +0000

    chore(homeassistant.docker-compose): update

[33mcommit 905af3df3c550023046eb5208788996d38286886[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Dec 18 22:48:36 2025 +0000

    chore(portainer.docker-compose): update

[33mcommit 0b0757691e21b13a5861ced68e4c2895d25087f6[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Dec 18 22:33:47 2025 +0000

    chore(.gitignore): mise a jour.

[33mcommit 0507e23114582aa968d9351927379ea298ddcc7d[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Dec 18 22:33:00 2025 +0000

    chore(env): mise a jour des variable

[33mcommit 63d1749e823fb0a1830d4b63fe49fe7ba10a108d[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Thu Dec 18 19:11:59 2025 +0000

    create Environnement Prod

[33mcommit 6c0bf23148c5dfc69238bf299b3183794f673434[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Wed Dec 17 23:02:55 2025 +0000

    ajout de variable #GENERAL dans .env

[33mcommit 223c616fe284084aa66f8d36e90b3a196c9bbd85[m
Merge: a8e69d6 b55e473
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Wed Dec 17 22:56:21 2025 +0000

    feat: fin de Neron-init

[33mcommit 007f26c8aa4b421b7e2801e9e1c96da4e72888bb[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Wed Dec 17 21:51:49 2025 +0000

    Remise en fonctionnement de plusieurs serices. (Portainer, HA, Dashboard, Monitoring, llama)

[33mcommit b55e47367f3f327d1311252a719390bf690da7af[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Tue Dec 16 20:57:42 2025 +0100

    git: reset

[33mcommit a8e69d67494b08f608491862c47baae8f8e80d4a[m
Author: enabeteleazar <161418955+enabeteleazar@users.noreply.github.com>
Date:   Tue Dec 16 14:32:55 2025 +0100

    Create tests

[33mcommit 399d8e3c212d230e40237f156d4d83de1133a3a5[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Dec 15 22:13:48 2025 +0100

    debug by Copilot Github

[33mcommit ec2e76814c49411936e5739ac2b6a2947b2fd849[m
Author: enabeteleazar <161418955+enabeteleazar@users.noreply.github.com>
Date:   Mon Dec 15 21:37:14 2025 +0100

    Update llm_core.py

[33mcommit 1f6f1e3e9fb5e13b587de8881efdb68450fa6d1a[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Dec 15 21:36:14 2025 +0100

    feat(neron_llm):Initial local LLM avec Ollama

[33mcommit d9e3a3d5c73e586a5814b1f1e5bd04de646e931f[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Dec 15 19:06:51 2025 +0100

    chore(neron_core): add state.py avec Constante.

[33mcommit e1f9686730306a2abe4c1287a401d9cd910d68f9[m
Author: enabeteleazar <161418955+enabeteleazar@users.noreply.github.com>
Date:   Mon Dec 15 18:59:03 2025 +0100

    Update state.py

[33mcommit 6991c127c6767b5e9f3052abc0bf35395884547b[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Mon Dec 15 16:59:07 2025 +0100

    feat(neron_core): final version stable, test fonctionnel.

[33mcommit dc9743065af417c7a0ca4d559b6d35d0df9d476b[m
Author: enabeteleazar <161418955+enabeteleazar@users.noreply.github.com>
Date:   Mon Dec 15 10:46:23 2025 +0100

    suppresion de neron-core & neron-llm

[33mcommit 4af8d43d430920d85a749b72ea2fa6121b29cc77[m
Author: enabeteleazar <161418955+enabeteleazar@users.noreply.github.com>
Date:   Mon Dec 15 10:42:35 2025 +0100

    Delete test.sh

[33mcommit af08407dd6671f23b9a6ebadee677ab9909de95d[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Dec 14 17:49:19 2025 +0100

    chore: Finalisation de Néron Core pour la phase actuelle.
    - main;py fonctionnel avec endpoints /, /health, /status, /chat.
    - Integration complete de NeronMessage & Orchestrator
    - Class MesssageRequest utilisée pour l reception de message JSON
    - Scripts test.sh ajouter pour tester facilement Néron Core
    - Module Stable, pret pour la prochaine etape (neron-llm & neron-io)

[33mcommit c6349a2b51bb6cbb329c99826f5eda0cb268f515[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Dec 14 17:24:13 2025 +0100

    test: Ajout du script test.sh pour tester neron Core.

[33mcommit 5801447bd7eb8a13f4748eca32449f8e25189458[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Dec 14 17:12:29 2025 +0100

    fix:Correction de la route /chat et du MessageRequest

[33mcommit ab29d327a57eb8beeee715f87d4d3628df60fd45[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Dec 14 16:50:01 2025 +0100

    feat: Ajout du module neron_core
    - creation de main.py - API fastAPI
    - Orchestrator.py -gestion des NeronMessage
    - Endpoint /chat: pret a recevoir des messages JSON

[33mcommit 0fcbb142a789181307325baa97c50d990d9928ce[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Dec 14 16:45:37 2025 +0100

    feat: ajout du modèe NeronMessage pour la communication interne.

[33mcommit b8b38c0949930708e629ee187208b494eee2f8f9[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sun Dec 14 14:55:13 2025 +0100

    refactor: Reorganisation des dossiers

[33mcommit 2a3f6070b7a441cbad0287f5596fecc9cb55ab40[m
Author: enabeteleazar <nabet.eleazar@gmail.com>
Date:   Sat Dec 13 20:27:54 2025 +0100

    Rearangement Arborescence
