"""
Configuration du Control Plane
Charge les paramètres depuis les variables d'environnement et config.yaml
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    """Classe de configuration centralisée"""
    
    def __init__(self, config_file: str = "config/config.yaml"):
        self.config_file = config_file
        self._load_config()
    
    def _load_config(self):
        """Charger la configuration depuis le fichier YAML et l'environnement"""
        
        # Configuration par défaut
        defaults = {
            'check_interval': 300,  # 5 minutes
            'check_timeout': 10,    # 10 secondes
            'max_response_time': 5.0,  # 5 secondes
            'retry_attempts': 3,
            'retry_delay': 30,
            'database_path': 'data/history.db'
        }
        
        # Charger depuis YAML si le fichier existe
        config_path = Path(self.config_file)
        if config_path.exists():
            with open(config_path, 'r') as f:
                yaml_config = yaml.safe_load(f) or {}
                defaults.update(yaml_config)
        
        # Variables obligatoires depuis l'environnement
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not self.telegram_bot_token or not self.telegram_chat_id:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN et TELEGRAM_CHAT_ID doivent être définis "
                "dans les variables d'environnement ou le fichier .env"
            )
        
        # URLs des services
        self.homebox_url = os.getenv('HOMEBOX_URL', defaults.get('homebox_url', 'http://localhost:7745'))
        self.neron_url = os.getenv('NERON_URL', defaults.get('neron_url', 'http://localhost:3000'))
        
        # Services Homebox multiples (optionnel)
        # Format: SERVICE_NAME:PORT,SERVICE_NAME:PORT
        # Ex: Homebox Main:7745,Homebox API:8080,Homebox DB:5432
        homebox_services_str = os.getenv('HOMEBOX_SERVICES', '')
        self.homebox_services = {}
        
        if homebox_services_str:
            # Parser les services
            for service in homebox_services_str.split(','):
                if ':' in service:
                    name, port = service.split(':', 1)
                    try:
                        self.homebox_services[name.strip()] = int(port.strip())
                    except ValueError:
                        logger.warning(f"Port invalide pour {name}: {port}")
            
            # Extraire l'URL de base depuis HOMEBOX_URL
            # Ex: http://192.168.1.130:7745 -> http://192.168.1.130
            if '://' in self.homebox_url:
                protocol, rest = self.homebox_url.split('://', 1)
                host = rest.split(':')[0]  # Enlever le port si présent
                self.homebox_base_url = f"{protocol}://{host}"
            else:
                self.homebox_base_url = self.homebox_url
        
        # Paramètres de vérification
        self.check_interval = int(os.getenv('CHECK_INTERVAL', defaults['check_interval']))
        self.check_timeout = int(os.getenv('CHECK_TIMEOUT', defaults['check_timeout']))
        self.max_response_time = float(os.getenv('MAX_RESPONSE_TIME', defaults['max_response_time']))
        self.retry_attempts = int(os.getenv('RETRY_ATTEMPTS', defaults['retry_attempts']))
        self.retry_delay = int(os.getenv('RETRY_DELAY', defaults['retry_delay']))
        
        # Vérification détaillée des services (Homebox API)
        self.check_homebox_services = os.getenv('CHECK_HOMEBOX_SERVICES', 'true').lower() == 'true'
        
        # Base de données
        self.database_path = os.getenv('DATABASE_PATH', defaults['database_path'])
        
        # Créer le dossier data si nécessaire
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
    
    def __repr__(self):
        return (
            f"Config(homebox={self.homebox_url}, "
            f"neron={self.neron_url}, "
            f"interval={self.check_interval}s)"
        )
