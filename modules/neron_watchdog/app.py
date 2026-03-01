#!/usr/bin/env python3
"""
Neron WatchDog - Monitoring System
Surveille l'état de Neron et Neron avec notifications Telegram
"""

import asyncio
import uvicorn
from src.watchers.docker_events import DockerEventWatcher
from src.collectors.system import SystemCollector
from src.actions.restart import RestartAction
from src.memory.strategic import StrategicMemory
from src.reports.daily import DailyReport
from src.detectors.anomaly import AnomalyDetector
from src.collectors.docker_stats import DockerStatsCollector
import logging
import sys
import os
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
import signal

# S'assurer que le module src est dans le path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from src.checkers.neron import NeronChecker
from src.notifiers.telegram import TelegramNotifier
from src.database.history import HistoryManager
from src.config import Config

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/control-plane.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class ServiceStatus:
    """Représente l'état d'un service"""
    def __init__(self, service_name: str, is_healthy: bool, 
                 response_time: float, status_code: int = None,
                 error: str = None):
        self.service_name = service_name
        self.is_healthy = is_healthy
        self.response_time = response_time
        self.status_code = status_code
        self.error = error
        self.timestamp = datetime.now()
    
    def __repr__(self):
        status = "✅ UP" if self.is_healthy else "🔴 DOWN"
        return f"{self.service_name}: {status} ({self.response_time:.2f}s)"


class ControlPlane:
    """Contrôleur principal du système de monitoring"""
    
    def __init__(self):
        self.config = Config()
        self.notifier = TelegramNotifier(
            token=self.config.telegram_bot_token,
            chat_id=self.config.telegram_chat_id
        )
        self.history = HistoryManager(self.config.database_path)
        
        # Initialiser les checkers
        self.checkers = []
        
        # Neron checker (depuis JSON)
        self.checkers.append(
            NeronChecker(
                config_file="config/neron.json",
                fallback_url=self.config.neron_url,
                fallback_timeout=self.config.check_timeout
            )
        )
        
        # État précédent pour détecter les changements
        self.previous_states: Dict[str, bool] = {}
        
        # Action de restart automatique
        self.memory = StrategicMemory()
        self.restart_action = RestartAction(self.notifier, memory=self.memory)
        self.docker_stats = DockerStatsCollector()
        self.anomaly_detector = AnomalyDetector(self.memory, self.notifier)
        self.daily_report = DailyReport(self.notifier, self.memory, self.docker_stats, self.anomaly_detector)
        self.running = False
        
        logger.info("WatchDog initialisé")
    
    async def check_service(self, checker) -> ServiceStatus:
        """Vérifier un service individuel"""
        try:
            result = await checker.check()
            
            # Sauvegarder dans l'historique
            self.history.add_check(
                service_name=result.service_name,
                is_healthy=result.is_healthy,
                response_time=result.response_time,
                status_code=result.status_code,
                error=result.error
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de {checker.name}: {e}")
            return ServiceStatus(
                service_name=checker.name,
                is_healthy=False,
                response_time=0,
                error=str(e)
            )
    
    async def check_all(self) -> List[ServiceStatus]:
        """Vérifier tous les services en parallèle"""
        logger.info("Début de la vérification de tous les services")
        
        # Exécuter tous les checks en parallèle
        tasks = [self.check_service(checker) for checker in self.checkers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Traiter les résultats et envoyer les notifications
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Exception lors du check: {result}")
                continue
            
            # Si le checker retourne des résultats individuels, les traiter un par un
            if hasattr(result, 'individual_results') and result.individual_results:
                for individual in result.individual_results:
                    await self.handle_result(individual)
            else:
                await self.handle_result(result)
        
        return [r for r in results if not isinstance(r, Exception)]
    
    async def retry_check(self, checker, delay: int = 10) -> ServiceStatus:
        """Re-vérifier un service après un délai"""
        logger.info(f"🔄 Retry dans {delay}s pour {checker.name}...")
        await asyncio.sleep(delay)
        return await self.check_service(checker)

    async def handle_result(self, result: ServiceStatus):
        """Gérer le résultat avec retry intelligent (Option 3)"""
        service_name = result.service_name
        was_healthy = self.previous_states.get(service_name, True)

        # Service est passé de UP à DOWN
        if was_healthy and not result.is_healthy:
            # Trouver le checker correspondant
            # Chercher dans les checkers individuels du NeronChecker
            checker = None
            for c in self.checkers:
                if hasattr(c, 'service_checkers'):
                    checker = next((sc for sc in c.service_checkers if sc.name == service_name), None)
                    if checker:
                        break
                elif c.name == service_name:
                    checker = c
                    break

            if checker:
                # Ne pas retry si restart_action gère déjà
                if self.restart_action.restart_counts.get(service_name, 0) > 0:
                    self.previous_states[service_name] = False
                    return
                # Retry après 10s avant d'alerter
                retry_result = await self.retry_check(checker, delay=10)

                if not retry_result.is_healthy:
                    # Toujours DOWN après retry -> alerte Telegram + auto-restart
                    logger.warning(f"🔴 {service_name} confirmé DOWN après retry")
                    message = (
                        f"🔴 <b>ALERTE - Service DOWN</b>\n\n"
                        f"<b>Service:</b> {service_name}\n"
                        f"<b>Status:</b> Indisponible\n"
                        f"<b>Code HTTP:</b> {result.status_code or 'N/A'}\n"
                        f"<b>Erreur:</b> {result.error or 'Timeout/Connexion impossible'}\n"
                        f"<b>Heure:</b> {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    if hasattr(result, 'details') and result.details:
                        message += f"\n\n<b>Détails:</b>\n{result.details}"
                    await self.notifier.send_alert(message)
                    self.previous_states[service_name] = False
                    # Lancer le pipeline de restart automatique
                    asyncio.create_task(
                        self.restart_action.handle_down(service_name, checker)
                    )
                else:
                    # Revenu UP entre les deux checks -> micro-coupure
                    logger.warning(f"⚡ Micro-coupure détectée sur {service_name} (revenu UP après retry)")
                    await self.notifier.send_info(
                        f"⚡ <b>Micro-coupure détectée</b>\n\n"
                        f"<b>Service:</b> {service_name}\n"
                        f"<b>Durée:</b> moins de 10s\n"
                        f"<b>Status:</b> Revenu UP automatiquement\n"
                        f"<b>Heure:</b> {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    return
            else:
                # Pas de checker trouvé -> alerte directe
                logger.warning(f"🔴 {service_name} est maintenant DOWN")
                message = (
                    f"🔴 <b>ALERTE - Service DOWN</b>\n\n"
                    f"<b>Service:</b> {service_name}\n"
                    f"<b>Status:</b> Indisponible\n"
                    f"<b>Code HTTP:</b> {result.status_code or 'N/A'}\n"
                    f"<b>Erreur:</b> {result.error or 'Timeout/Connexion impossible'}\n"
                    f"<b>Heure:</b> {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                )
                if hasattr(result, 'details') and result.details:
                    message += f"\n\n<b>Détails:</b>\n{result.details}"
                await self.notifier.send_alert(message)
        
        # Service est revenu UP
        elif not was_healthy and result.is_healthy:
            self.restart_action.reset_counter(service_name)
            logger.info(f"🟢 {service_name} est revenu UP")
        
        # Service est UP mais lent
        elif result.is_healthy and result.response_time > self.config.max_response_time:
            logger.warning(f"⚠️ {service_name} est lent ({result.response_time:.2f}s)")
            message = (
                f"⚠️ <b>AVERTISSEMENT - Performance dégradée</b>\n\n"
                f"<b>Service:</b> {service_name}\n"
                f"<b>Temps de réponse:</b> {result.response_time:.2f}s\n"
                f"<b>Seuil:</b> {self.config.max_response_time}s\n"
                f"<b>Heure:</b> {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            await self.notifier.send_warning(message)
        
        # Service toujours DOWN - le watchdog gère déjà le restart
        elif not result.is_healthy:
            logger.debug(f"🔴 {service_name} toujours DOWN ({result.response_time:.2f}s)")
        # Service est OK
        else:
            logger.info(f"✅ {service_name} OK ({result.response_time:.2f}s)")
        
        # Mettre à jour l'état précédent
        self.previous_states[service_name] = result.is_healthy
    
    async def send_status_report(self):
        """Envoyer un rapport de statut complet"""
        logger.info("Génération du rapport de statut")
        
        # Récupérer les derniers checks
        results = await self.check_all()
        
        # Construire le message
        report = "📊 <b>RAPPORT DE STATUT</b>\n\n"
        
        for result in results:
            status_icon = "✅" if result.is_healthy else "🔴"
            report += (
                f"{status_icon} <b>{result.service_name}</b>\n"
                f"   Status: {'UP' if result.is_healthy else 'DOWN'}\n"
                f"   Réponse: {result.response_time:.2f}s\n"
            )
            if result.status_code:
                report += f"   Code HTTP: {result.status_code}\n"
            if result.error:
                report += f"   Erreur: {result.error}\n"
            report += "\n"
        
        # Ajouter les statistiques
        stats = self.history.get_uptime_stats(hours=24)
        if stats:
            report += "📈 <b>STATISTIQUES 24H</b>\n\n"
            for service, uptime in stats.items():
                report += f"   {service}: {uptime:.1f}% uptime\n"
        
        report += f"\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        await self.notifier.send_info(report)
    
    async def run_continuous(self):
        """Boucle de monitoring continue"""
        self.running = True
        interval = self.config.check_interval
        
        logger.info(f"🚀 Démarrage du monitoring continu (intervalle: {interval}s)")
        
        # Démarrer le watchdog Docker Events en parallèle
        # Construire le dict des checkers individuels
        individual_checkers = {}
        for c in self.checkers:
            if hasattr(c, 'service_checkers'):
                for sc in c.service_checkers:
                    individual_checkers[sc.name] = sc

        watcher = DockerEventWatcher(
            self.notifier,
            self.previous_states,
            self.restart_action.restart_counts,
            self.restart_action,
            individual_checkers,
            control_plane=self
        )
        asyncio.create_task(watcher.watch())
        logger.info("👁️ Docker Event Watcher lancé en parallèle")
        
        # Envoyer une notification de démarrage
        await self.notifier.send_info(
            "🚀 <b>WatchDog démarré</b>\n\n"
            f"Monitoring de {len(self.checkers)} services:\n"
            + "\n".join(f"  • {c.name}" for c in self.checkers) +
            f"\n\nIntervalle: {interval}s"
        )
        
        check_count = 0
        system_collector = SystemCollector()
        
        try:
            while self.running:
                check_count += 1
                logger.info(f"--- Check #{check_count} ---")
                # Purge hebdomadaire
                if check_count % 100 == 0:
                    self.memory.purge_old_entries()
                
                await self.check_all()
                
                # Collecter et verifier les metriques systeme
                metrics = system_collector.collect()
                alerts = system_collector.check_thresholds(metrics)
                
                for level, msg in alerts:
                    logger.warning(f"📊 {msg}")
                    if level == "critical":
                        await self.notifier.send_alert(
                            f"🔴 <b>ALERTE SYSTÈME</b>\n\n"
                            f"{msg}\n"
                            f"<b>Heure:</b> {metrics.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                    else:
                        await self.notifier.send_warning(
                            f"⚠️ <b>AVERTISSEMENT SYSTÈME</b>\n\n"
                            f"{msg}\n"
                            f"<b>Heure:</b> {metrics.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                
                # Envoyer un rapport toutes les 24h (86400 secondes)
                if check_count * interval % 86400 == 0:
                    await self.send_status_report()
                
                # Rapport quotidien à 19h
                if self.daily_report.should_send():
                    await self.daily_report.send()

                # Stats Docker toutes les 5 minutes
                if check_count % 5 == 0:
                    docker_stats = await self.docker_stats.collect_all()
                    # Stocker dans mémoire JSONL
                    self.memory.record_container_stats(docker_stats)
                    alerts = self.docker_stats.check_thresholds(docker_stats)
                    for level, msg in alerts:
                        logger.warning(msg)
                        if level == 'critical':
                            await self.notifier.send_alert(
                                f"🔴 <b>ALERTE CONTENEUR</b>\n\n{msg}\n"
                                f"<b>Heure:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                            )
                        else:
                            await self.notifier.send_warning(
                                f"⚠️ <b>AVERTISSEMENT CONTENEUR</b>\n\n{msg}\n"
                                f"<b>Heure:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                            )
                    if check_count % 60 == 0:
                        logger.info(self.docker_stats.format_summary(docker_stats))

                # Analyse anomalies toutes les heures
                if check_count % 60 == 0:
                    await self.anomaly_detector.run_analysis(days=7)

                # Attendre avant le prochain check
                await asyncio.sleep(interval)
                
        except asyncio.CancelledError:
            logger.info("Monitoring arrêté (CancelledError)")
        except Exception as e:
            logger.error(f"Erreur dans la boucle de monitoring: {e}")
            await self.notifier.send_alert(
                f"❌ <b>ERREUR CRITIQUE</b>\n\n"
                f"Le système de monitoring a rencontré une erreur:\n"
                f"{str(e)}"
            )
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Arrêt propre du système"""
        logger.info("Arrêt du WatchDog...")
        self.running = False
        
        # Envoyer une notification d'arrêt
        await self.notifier.send_info(
            "🛑 <b>WatchDog arrêté</b>\n\n"
            f"Arrêt à {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        # Fermer les connexions
        self.history.close()
        logger.info("WatchDog arrêté proprement")



# ─────────────────────────────────────────────
# API HTTP
# ─────────────────────────────────────────────
from fastapi import FastAPI, HTTPException

api = FastAPI(title="Neron WatchDog API", version="1.0.0")


@api.get("/health")
def health():
    return {"status": "healthy", "service": "neron_watchdog"}


@api.get("/status")
async def status():
    """État de tous les services"""
    if control_plane is None:
        return {"services": {}}
    results = await control_plane.check_all()
    services = {}
    for r in results:
        # Résultats individuels (multi-services dans un checker)
        if hasattr(r, 'individual_results') and r.individual_results:
            for individual in r.individual_results:
                services[individual.service_name] = {
                    "healthy": individual.is_healthy,
                    "response_time": individual.response_time,
                    "error": individual.error
                }
        else:
            services[r.service_name] = {
                "healthy": r.is_healthy,
                "response_time": r.response_time,
                "error": r.error
            }
    return {"services": services}


@api.get("/score")
def score():
    """Score de santé global"""
    if control_plane is None:
        return {}
    entries = control_plane.memory.read_all(days=7)
    return control_plane.anomaly_detector.compute_health_score(entries)


@api.get("/anomalies")
async def anomalies():
    """Anomalies détectées"""
    if control_plane is None:
        return {"anomalies": []}
    entries = control_plane.memory.read_all(days=7)
    results = []
    for detector in [
        control_plane.anomaly_detector.detect_recurring_crash,
        control_plane.anomaly_detector.detect_cascade,
        control_plane.anomaly_detector.detect_crash_after_restart,
        control_plane.anomaly_detector.detect_increasing_frequency,
    ]:
        results.extend(detector(entries))
    return {"anomalies": results}


@api.get("/docker-stats")
async def docker_stats():
    """Stats Docker par conteneur"""
    if control_plane is None:
        return {"stats": {}}
    snapshot = await control_plane.docker_stats.collect_all()
    stats = {}
    for name, s in snapshot.items():
        stats[name] = {
            "cpu": s.cpu_percent,
            "ram_mb": s.ram_mb,
            "ram_percent": s.ram_percent,
            "status": s.status
        }
    return {"stats": stats}


@api.post("/rapport")
async def rapport():
    """Envoyer le rapport immédiatement"""
    if control_plane is None:
        return {"status": "error"}
    await control_plane.daily_report.send()
    return {"status": "sent"}


@api.post("/pause")
def pause():
    """Mettre le watchdog en pause"""
    if control_plane:
        control_plane.running = False
    return {"status": "paused"}


@api.post("/resume")
def resume():
    """Reprendre le watchdog"""
    if control_plane:
        control_plane.running = True
    return {"status": "resumed"}


@api.post("/restart/{service_name}")
async def restart_service(service_name: str):
    """Redémarrer un service manuellement"""
    if control_plane is None:
        return {"status": "error"}
    try:
        await control_plane.restart_action.restart_container(service_name)
        return {"status": "restarted", "service": service_name}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Variable globale pour accès depuis l'API
control_plane = None

async def main():
    """Point d'entrée principal"""
    global control_plane
    cp = ControlPlane()
    control_plane = cp
    
    # Gérer les signaux d'arrêt proprement
    def signal_handler(sig, frame):
        logger.info(f"Signal {sig} reçu, arrêt en cours...")
        cp.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Mode de fonctionnement
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "check":
            # Une seule vérification
            logger.info("Mode: Vérification unique")
            await cp.check_all()
        
        elif command == "report":
            # Envoyer un rapport
            logger.info("Mode: Rapport de statut")
            await cp.send_status_report()
        
        else:
            print(f"Commande inconnue: {command}")
            print("Usage: python app.py [check|report]")
            sys.exit(1)
    else:
        # Mode monitoring continu (par défaut)
        logger.info("Mode: Monitoring continu")
        config = uvicorn.Config(api, host='0.0.0.0', port=8003, log_level='warning')
    server = uvicorn.Server(config)
    await asyncio.gather(
        cp.run_continuous(),
        server.serve()
    )




@api.get("/logs/{service_name}")
async def get_logs(service_name: str, lines: int = 50):
    """Dernières lignes de logs d'un conteneur via socket Docker"""
    import http.client
    import json as _json
    try:
        conn = http.client.HTTPConnection("localhost", timeout=10)
        conn.sock = __import__('socket').socket(__import__('socket').AF_UNIX)
        conn.sock.connect("/var/run/docker.sock")
        conn.request("GET", f"/containers/{service_name}/logs?tail={lines}&stdout=1&stderr=1")
        resp = conn.getresponse()
        if resp.status == 404:
            raise HTTPException(404, f"Conteneur {service_name} introuvable")
        raw = resp.read()
        # Supprimer les headers de stream Docker (8 bytes par ligne)
        lines_out = []
        i = 0
        while i < len(raw):
            if i + 8 <= len(raw):
                size = int.from_bytes(raw[i+4:i+8], 'big')
                line = raw[i+8:i+8+size].decode('utf-8', errors='replace').rstrip()
                if line:
                    lines_out.append(line)
                i += 8 + size
            else:
                break
        return {"service": service_name, "logs": lines_out}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@api.get("/history/{service_name}")
async def get_history(service_name: str, days: int = 7):
    """Historique des crashs d'un service depuis la mémoire JSONL"""
    if control_plane is None:
        return {"service": service_name, "events": []}
    entries = control_plane.memory.read_all(days=days)
    events = [
        e for e in entries
        if e.get("service") == service_name and e.get("type") in ("crash", "restart", "instability", "recovery")
    ]
    return {
        "service": service_name,
        "days": days,
        "total": len(events),
        "events": events[-50:]
    }
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Arrêt demandé par l'utilisateur")
    except Exception as e:
        logger.error(f"Erreur fatale: {e}", exc_info=True)
        sys.exit(1)


@api.get("/logs/{service_name}")
async def get_logs(service_name: str, lines: int = 50):
    """Dernières lignes de logs d'un conteneur via socket Docker"""
    import http.client
    import json as _json
    try:
        conn = http.client.HTTPConnection("localhost", timeout=10)
        conn.sock = __import__('socket').socket(__import__('socket').AF_UNIX)
        conn.sock.connect("/var/run/docker.sock")
        conn.request("GET", f"/containers/{service_name}/logs?tail={lines}&stdout=1&stderr=1")
        resp = conn.getresponse()
        if resp.status == 404:
            raise HTTPException(404, f"Conteneur {service_name} introuvable")
        raw = resp.read()
        # Supprimer les headers de stream Docker (8 bytes par ligne)
        lines_out = []
        i = 0
        while i < len(raw):
            if i + 8 <= len(raw):
                size = int.from_bytes(raw[i+4:i+8], 'big')
                line = raw[i+8:i+8+size].decode('utf-8', errors='replace').rstrip()
                if line:
                    lines_out.append(line)
                i += 8 + size
            else:
                break
        return {"service": service_name, "logs": lines_out}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@api.get("/history/{service_name}")
async def get_history(service_name: str, days: int = 7):
    """Historique des crashs d'un service depuis la mémoire JSONL"""
    if control_plane is None:
        return {"service": service_name, "events": []}
    entries = control_plane.memory.read_all(days=days)
    events = [
        e for e in entries
        if e.get("service") == service_name and e.get("type") in ("crash", "restart", "instability", "recovery")
    ]
    return {
        "service": service_name,
        "days": days,
        "total": len(events),
        "events": events[-50:]  # max 50 entrées
    }
