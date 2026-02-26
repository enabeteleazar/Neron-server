#!/usr/bin/env python3
"""
Neron Control Plane - Monitoring System
Surveille l'état de Neron et Neron avec notifications Telegram
"""

import asyncio
from src.watchers.docker_events import DockerEventWatcher
from src.collectors.system import SystemCollector
from src.actions.restart import RestartAction
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
        self.restart_action = RestartAction(self.notifier)
        self.running = False
        
        logger.info("Control Plane initialisé")
    
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
            individual_checkers
        )
        asyncio.create_task(watcher.watch())
        logger.info("👁️ Docker Event Watcher lancé en parallèle")
        
        # Envoyer une notification de démarrage
        await self.notifier.send_info(
            "🚀 <b>Control Plane démarré</b>\n\n"
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
        logger.info("Arrêt du Control Plane...")
        self.running = False
        
        # Envoyer une notification d'arrêt
        await self.notifier.send_info(
            "🛑 <b>Control Plane arrêté</b>\n\n"
            f"Arrêt à {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        # Fermer les connexions
        self.history.close()
        logger.info("Control Plane arrêté proprement")


async def main():
    """Point d'entrée principal"""
    cp = ControlPlane()
    
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
        await cp.run_continuous()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Arrêt demandé par l'utilisateur")
    except Exception as e:
        logger.error(f"Erreur fatale: {e}", exc_info=True)
        sys.exit(1)
