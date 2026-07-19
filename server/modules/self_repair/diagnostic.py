from __future__ import annotations

from typing import Any


def diagnose_alert(payload: dict[str, Any]) -> dict[str, Any]:
    reason = payload.get("reason")
    agent = payload.get("agent")
    execution_time_ms = payload.get("execution_time_ms")

    if reason == "agent_execution_slow":
        return {
            "kind": "performance",
            "severity": "medium",
            "summary": f"L’agent {agent} est lent.",
            "probable_causes": [
                "modèle LLM trop lent",
                "charge CPU/RAM élevée",
                "timeout trop permissif",
                "seuil d’alerte trop bas pour cet agent",
            ],
            "safe_actions": [
                "vérifier CPU/RAM",
                "consulter les derniers événements",
                "adapter le seuil de lenteur par agent",
                "utiliser un modèle plus léger",
            ],
            "metadata": {
                "agent": agent,
                "execution_time_ms": execution_time_ms,
            },
        }

    if reason == "agent_execution_failed":
        return {
            "kind": "failure",
            "severity": "high",
            "summary": f"L’agent {agent} a échoué.",
            "probable_causes": [
                "exception Python",
                "mauvaise configuration",
                "dépendance absente",
                "réponse LLM invalide",
            ],
            "safe_actions": [
                "lire les logs de l’agent",
                "analyser l’erreur",
                "corriger dans workspace",
                "tester avant validation",
            ],
            "metadata": {
                "agent": agent,
            },
        }

    if reason == "agent_instability":
        return {
            "kind": "stability",
            "severity": "high",
            "summary": f"L’agent {agent} semble instable.",
            "probable_causes": [
                "échecs répétés",
                "bug intermittent",
                "ressource externe indisponible",
            ],
            "safe_actions": [
                "désactiver temporairement l’agent",
                "lancer un audit",
                "corriger en workspace",
            ],
            "metadata": payload,
        }

    if reason == "high_cpu":
        cpu = payload.get("cpu_usage")
        return {
            "kind": "resource",
            "severity": "high" if (cpu or 0) >= 95 else "medium",
            "summary": f"Charge CPU élevée ({cpu}%).",
            "probable_causes": [
                "stratégie LLM 'parallel' faisant courir plusieurs modèles",
                "inférence locale (Ollama/llama.cpp) saturant les cœurs",
                "boucle autonome (cognitive/self/world model) trop fréquente",
                "transcription STT (faster-whisper) en cours",
            ],
            "safe_actions": [
                "identifier le processus dominant (ps aux --sort=-%cpu | head)",
                "passer strategy.code de 'parallel' à 'single' dans neron.yaml",
                "espacer les boucles autonomes (intervalle plus long)",
                "limiter les threads Ollama (OLLAMA_NUM_PARALLEL=1)",
            ],
            "metadata": payload,
        }

    if reason in ("high_ram", "high_memory"):
        return {
            "kind": "resource",
            "severity": "high",
            "summary": "Mémoire vive saturée.",
            "probable_causes": [
                "modèle LLM trop grand pour la RAM disponible",
                "plusieurs modèles chargés simultanément",
                "fuite mémoire dans un service longue durée",
            ],
            "safe_actions": [
                "décharger les modèles inutilisés (ollama stop)",
                "utiliser un modèle plus petit dans model_map",
                "redémarrer le service dont la RSS croît sans redescendre",
            ],
            "metadata": payload,
        }

    if reason == "high_disk":
        return {
            "kind": "resource",
            "severity": "medium",
            "summary": "Espace disque faible.",
            "probable_causes": [
                "modèles LLM accumulés (~/.ollama, data/models)",
                "logs sans rotation effective",
                "caches de build (.next, __pycache__, pip)",
            ],
            "safe_actions": [
                "lister les plus gros répertoires (du -sh /* 2>/dev/null | sort -h)",
                "supprimer les modèles inutilisés (ollama rm)",
                "purger les caches (make clean, .next/cache)",
                "vérifier la rotation des logs (logs.max_size_mb)",
            ],
            "metadata": payload,
        }

    return {
        "kind": "unknown",
        "severity": "low",
        "summary": f"Alerte non reconnue : {reason}",
        "probable_causes": ["cause inconnue"],
        "safe_actions": ["inspection manuelle recommandée"],
        "metadata": payload,
    }
