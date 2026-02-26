"""
Neron Service Checker - Configuration JSON
Lit la configuration depuis config/neron.json

Structure du fichier JSON:
{
  "base_url": "http://192.168.1.130",
  "services": [
    {
      "name": "Neron Main",
      "port": 3000,
      "enabled": true,
      "description": "Service principal",
      "critical": true
    }
  ],
  "settings": {
    "timeout": 10,
    "max_response_time": 5.0
  }
}
"""

import aiohttp
import asyncio
import time
import logging
import json
from pathlib import Path
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class NeronServiceChecker:
    """Vérificateur pour un service Neron individuel"""
    
    def __init__(self, name: str, url: str, health_path: str = "/health", timeout: int = 10, critical: bool = True, description: str = None, ssl_verify: bool = True):
        """
        Args:
            name: Nom du service
            url: URL complète avec port
            timeout: Timeout en secondes
            critical: Si True, une panne déclenche une alerte critique
            description: Description du service (optionnel)
        """
        self.name = name
        self.url = url.rstrip('/')
        self.health_path = health_path
        self.full_url = f"{self.url}{health_path}"
        self.timeout = timeout
        self.critical = critical
        self.description = description
        self.ssl_verify = ssl_verify
        logger.info(f"✓ {name} checker initialisé: {url}" + 
                   (f" ({description})" if description else ""))
    
    async def check(self):
        """Vérifier l'état du service"""
        from app import ServiceStatus
        
        start_time = time.time()
        
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            connector = aiohttp.TCPConnector(ssl=self.ssl_verify)
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                async with session.get(self.full_url) as response:
                    response_time = time.time() - start_time
                    
                    # 200 = OK, 401 = Auth required mais service UP
                    is_healthy = response.status in [200, 401]
                    
                    if is_healthy:
                        logger.debug(f"✅ {self.name}: UP ({response_time:.2f}s)")
                    else:
                        logger.warning(f"❌ {self.name}: DOWN (HTTP {response.status})")
                    
                    result = ServiceStatus(
                        service_name=self.name,
                        is_healthy=is_healthy,
                        response_time=response_time,
                        status_code=response.status,
                        error=None if is_healthy else f"HTTP {response.status}"
                    )
                    
                    # Ajouter les attributs personnalisés
                    result.critical = self.critical
                    result.description = self.description
                    
                    return result
        
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            logger.error(f"⏱️ {self.name}: Timeout après {self.timeout}s")
            result = ServiceStatus(
                service_name=self.name,
                is_healthy=False,
                response_time=response_time,
                error=f"Timeout après {self.timeout}s"
            )
            result.critical = self.critical
            result.description = self.description
            return result
        
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"❌ {self.name}: {str(e)}")
            result = ServiceStatus(
                service_name=self.name,
                is_healthy=False,
                response_time=response_time,
                error=str(e)
            )
            result.critical = self.critical
            result.description = self.description
            return result


class NeronChecker:
    """
    Vérificateur Neron avec configuration JSON
    
    Lit la configuration depuis config/neron.json
    """
    
    def __init__(self, config_file: str = "config/neron.json", 
                 fallback_url: str = None, fallback_timeout: int = 10):
        """
        Args:
            config_file: Chemin vers le fichier JSON de configuration
            fallback_url: URL de fallback si le JSON n'existe pas
            fallback_timeout: Timeout de fallback
        """
        self.name = "Neron"
        self.config_file = Path(config_file)
        self.service_checkers = []
        
        # Charger la configuration depuis le JSON
        if self.config_file.exists():
            logger.info(f"📄 Chargement de la configuration depuis {config_file}")
            self._load_from_json()
        elif fallback_url:
            logger.warning(f"⚠️ Fichier {config_file} non trouvé, utilisation du fallback")
            self._load_fallback(fallback_url, fallback_timeout)
        else:
            logger.error(f"❌ Fichier {config_file} non trouvé et pas de fallback")
        
        logger.info(f"✅ Neron checker initialisé avec {len(self.service_checkers)} service(s)")
    
    def _load_from_json(self):
        """Charger la configuration depuis le fichier JSON"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            base_url = config.get('base_url', 'http://localhost')
            services = config.get('services', [])
            settings = config.get('settings', {})
            
            # Extraire les paramètres
            timeout = settings.get('timeout', 10)
            self.max_response_time = settings.get('max_response_time', 5.0)
            self.check_parallel = settings.get('check_parallel', True)
            
            logger.info(f"🔧 Configuration chargée:")
            logger.info(f"   URL de base: {base_url}")
            logger.info(f"   Timeout: {timeout}s")
            logger.info(f"   Max response time: {self.max_response_time}s")
            logger.info(f"   Services configurés:")
            
            # Créer un checker pour chaque service activé
            for service in services:
                if not service.get('enabled', True):
                    logger.info(f"   ⊗ {service['name']} (désactivé)")
                    continue
                
                name = service['name']
                port = service['port']
                host = service.get('host', base_url.replace('http://', '').replace('https://', ''))
                ssl_verify = service.get('ssl_verify', True)
                scheme = "https" if not ssl_verify else "http"
                url = f"{scheme}://{host}:{port}"
                health_path = service.get('health_path', '/health')
                critical = service.get('critical', True)
                description = service.get('description')
                
                checker = NeronServiceChecker(
                    name=name,
                    url=url,
                    health_path=health_path,
                    timeout=timeout,
                    critical=critical,
                    description=description,
                    ssl_verify=ssl_verify
                )
                self.service_checkers.append(checker)
                
                # Afficher dans les logs
                critical_marker = "🔴" if critical else "🟡"
                logger.info(f"      {critical_marker} {name}:{port}")
        
        except json.JSONDecodeError as e:
            logger.error(f"❌ Erreur de parsing JSON: {e}")
            logger.error(f"   Vérifiez la syntaxe de {self.config_file}")
        except Exception as e:
            logger.error(f"❌ Erreur lors du chargement de la configuration: {e}")
    
    def _load_fallback(self, url: str, timeout: int):
        """Charger une configuration de fallback simple"""
        logger.info(f"🔧 Utilisation de la configuration fallback")
        logger.info(f"   URL: {url}")
        
        checker = NeronServiceChecker(
            name="Neron",
            url=url,
            timeout=timeout,
            critical=True,
            description="Service unique (fallback)"
        )
        self.service_checkers.append(checker)
        self.max_response_time = 5.0
        self.check_parallel = True
    
    def reload_config(self):
        """Recharger la configuration depuis le JSON"""
        logger.info("🔄 Rechargement de la configuration...")
        self.service_checkers = []
        self._load_from_json()
    
    async def check(self):
        """Vérifier tous les services"""
        from app import ServiceStatus
        
        if not self.service_checkers:
            return ServiceStatus(
                service_name=self.name,
                is_healthy=False,
                response_time=0,
                error="Aucun service configuré"
            )
        
        logger.debug(f"🔍 Vérification de {len(self.service_checkers)} service(s)...")
        
        # Vérifier en parallèle ou séquentiel
        start_time = time.time()
        
        if self.check_parallel:
            results = await asyncio.gather(
                *[checker.check() for checker in self.service_checkers],
                return_exceptions=True
            )
        else:
            results = []
            for checker in self.service_checkers:
                result = await checker.check()
                results.append(result)
        
        total_check_time = time.time() - start_time
        
        # Filtrer les résultats valides
        valid_results = [r for r in results if not isinstance(r, Exception)]
        
        if not valid_results:
            return ServiceStatus(
                service_name=self.name,
                is_healthy=False,
                response_time=total_check_time,
                error="Toutes les vérifications ont échoué"
            )
        
        # Si un seul service, retourner directement
        if len(valid_results) == 1:
            return valid_results[0]
        
        # ===== Agrégation pour multi-services =====
        
        all_healthy = all(r.is_healthy for r in valid_results)
        total_time = sum(r.response_time for r in valid_results)
        avg_time = total_time / len(valid_results)
        
        # Construire les détails
        details_lines = []
        down_services = []
        critical_down = []
        up_count = 0
        
        for result in valid_results:
            # Icône selon statut et criticité
            if result.is_healthy:
                status_icon = "✅"
                status_text = "UP"
                up_count += 1
            else:
                # Service DOWN
                critical_marker = "🔴" if hasattr(result, 'critical') and result.critical else "🟡"
                status_icon = critical_marker
                status_text = "DOWN"
                down_services.append(result.service_name)
                
                if hasattr(result, 'critical') and result.critical:
                    critical_down.append(result.service_name)
            
            # Ajouter description si disponible
            desc = ""
            if hasattr(result, 'description') and result.description:
                desc = f" - {result.description}"
            
            details_lines.append(
                f"{status_icon} {result.service_name}: "
                f"{status_text} ({result.response_time:.2f}s){desc}"
            )
        
        details = "\n   ".join(details_lines)
        
        # Message d'erreur
        error_msg = None
        if critical_down:
            error_msg = f"Services critiques DOWN: {', '.join(critical_down)}"
        elif down_services:
            error_msg = f"Services DOWN: {', '.join(down_services)}"
        
        # Log
        if critical_down:
            logger.error(f"🔴 Services critiques DOWN: {', '.join(critical_down)}")
        elif down_services:
            logger.warning(f"🟡 Services non-critiques DOWN: {', '.join(down_services)}")
        else:
            logger.info(f"✅ Tous les services UP ({up_count}/{len(valid_results)})")
        
        # Résultat agrégé
        result = ServiceStatus(
            service_name=self.name,
            is_healthy=all_healthy,
            response_time=avg_time,
            status_code=200 if all_healthy else 503,
            error=error_msg
        )
        result.details = details
        result.individual_results = valid_results
        
        logger.info(f"📊 Résumé:\n   {details}")
        
        return result
