"""
History Manager
Gère l'historique des vérifications dans une base SQLite
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class HistoryManager:
    """Gestionnaire de l'historique des vérifications"""
    
    def __init__(self, db_path: str = "data/history.db"):
        self.db_path = db_path
        
        # Créer le dossier si nécessaire
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialiser la base de données
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # Pour accéder aux colonnes par nom
        self._create_tables()
        
        logger.info(f"Base de données d'historique initialisée: {db_path}")
    
    def _create_tables(self):
        """Créer les tables nécessaires"""
        cursor = self.conn.cursor()
        
        # Table des vérifications
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                is_healthy BOOLEAN NOT NULL,
                response_time REAL NOT NULL,
                status_code INTEGER,
                error TEXT
            )
        """)
        
        # Index pour améliorer les performances des requêtes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_checks_service_time 
            ON checks(service_name, timestamp DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_checks_timestamp 
            ON checks(timestamp DESC)
        """)
        
        self.conn.commit()
    
    def add_check(self, service_name: str, is_healthy: bool, 
                  response_time: float, status_code: Optional[int] = None,
                  error: Optional[str] = None):
        """
        Ajouter une vérification à l'historique
        
        Args:
            service_name: Nom du service
            is_healthy: Service en bonne santé ?
            response_time: Temps de réponse en secondes
            status_code: Code HTTP (optionnel)
            error: Message d'erreur (optionnel)
        """
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                INSERT INTO checks (service_name, timestamp, is_healthy, response_time, status_code, error)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                service_name,
                datetime.now(),
                is_healthy,
                response_time,
                status_code,
                error
            ))
            
            self.conn.commit()
            logger.debug(f"Check enregistré: {service_name} - {'OK' if is_healthy else 'FAIL'}")
            
        except sqlite3.Error as e:
            logger.error(f"Erreur lors de l'enregistrement du check: {e}")
    
    def get_recent_checks(self, service_name: Optional[str] = None, 
                         limit: int = 100) -> List[Dict]:
        """
        Récupérer les vérifications récentes
        
        Args:
            service_name: Nom du service (None = tous)
            limit: Nombre maximum de résultats
        
        Returns:
            Liste des vérifications
        """
        try:
            cursor = self.conn.cursor()
            
            if service_name:
                cursor.execute("""
                    SELECT * FROM checks 
                    WHERE service_name = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (service_name, limit))
            else:
                cursor.execute("""
                    SELECT * FROM checks 
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        except sqlite3.Error as e:
            logger.error(f"Erreur lors de la récupération des checks: {e}")
            return []
    
    def get_uptime_stats(self, hours: int = 24) -> Dict[str, float]:
        """
        Calculer les statistiques d'uptime
        
        Args:
            hours: Période en heures
        
        Returns:
            Dictionnaire {service_name: uptime_percentage}
        """
        try:
            cursor = self.conn.cursor()
            since = datetime.now() - timedelta(hours=hours)
            
            cursor.execute("""
                SELECT 
                    service_name,
                    COUNT(*) as total_checks,
                    SUM(CASE WHEN is_healthy = 1 THEN 1 ELSE 0 END) as healthy_checks
                FROM checks
                WHERE timestamp > ?
                GROUP BY service_name
            """, (since,))
            
            rows = cursor.fetchall()
            
            stats = {}
            for row in rows:
                service_name = row['service_name']
                total = row['total_checks']
                healthy = row['healthy_checks']
                
                if total > 0:
                    uptime = (healthy / total) * 100
                    stats[service_name] = uptime
            
            return stats
            
        except sqlite3.Error as e:
            logger.error(f"Erreur lors du calcul des stats: {e}")
            return {}
    
    def get_downtime_incidents(self, hours: int = 24) -> List[Dict]:
        """
        Récupérer les incidents de downtime
        
        Args:
            hours: Période en heures
        
        Returns:
            Liste des incidents
        """
        try:
            cursor = self.conn.cursor()
            since = datetime.now() - timedelta(hours=hours)
            
            cursor.execute("""
                SELECT 
                    service_name,
                    timestamp,
                    response_time,
                    status_code,
                    error
                FROM checks
                WHERE timestamp > ? AND is_healthy = 0
                ORDER BY timestamp DESC
            """, (since,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        except sqlite3.Error as e:
            logger.error(f"Erreur lors de la récupération des incidents: {e}")
            return []
    
    def get_average_response_time(self, service_name: str, hours: int = 24) -> Optional[float]:
        """
        Calculer le temps de réponse moyen
        
        Args:
            service_name: Nom du service
            hours: Période en heures
        
        Returns:
            Temps de réponse moyen en secondes, ou None
        """
        try:
            cursor = self.conn.cursor()
            since = datetime.now() - timedelta(hours=hours)
            
            cursor.execute("""
                SELECT AVG(response_time) as avg_time
                FROM checks
                WHERE service_name = ? AND timestamp > ? AND is_healthy = 1
            """, (service_name, since))
            
            row = cursor.fetchone()
            return row['avg_time'] if row else None
            
        except sqlite3.Error as e:
            logger.error(f"Erreur lors du calcul du temps moyen: {e}")
            return None
    
    def cleanup_old_records(self, days: int = 30):
        """
        Nettoyer les anciens enregistrements
        
        Args:
            days: Supprimer les enregistrements plus vieux que X jours
        """
        try:
            cursor = self.conn.cursor()
            cutoff = datetime.now() - timedelta(days=days)
            
            cursor.execute("""
                DELETE FROM checks
                WHERE timestamp < ?
            """, (cutoff,))
            
            deleted = cursor.rowcount
            self.conn.commit()
            
            logger.info(f"Nettoyage: {deleted} enregistrements supprimés (> {days} jours)")
            
        except sqlite3.Error as e:
            logger.error(f"Erreur lors du nettoyage: {e}")
    
    def close(self):
        """Fermer la connexion à la base de données"""
        if self.conn:
            self.conn.close()
            logger.info("Connexion à la base de données fermée")
