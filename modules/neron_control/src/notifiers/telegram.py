"""
Telegram Notifier
Envoie des notifications via Telegram Bot
"""

import aiohttp
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Gestionnaire des notifications Telegram"""
    
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
        
        logger.info(f"Telegram notifier initialisé (chat_id: {chat_id})")
    
    async def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """
        Envoyer un message Telegram
        
        Args:
            text: Texte du message
            parse_mode: Mode de parsing (HTML ou Markdown)
        
        Returns:
            True si envoyé avec succès, False sinon
        """
        try:
            url = f"{self.base_url}/sendMessage"
            
            payload = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': parse_mode
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        logger.debug("Message Telegram envoyé avec succès")
                        return True
                    else:
                        error_data = await response.text()
                        logger.error(f"Erreur lors de l'envoi du message Telegram: {response.status} - {error_data}")
                        return False
        
        except Exception as e:
            logger.error(f"Exception lors de l'envoi du message Telegram: {e}")
            return False
    
    async def send_alert(self, message: str) -> bool:
        """
        Envoyer une alerte critique (rouge)
        
        Args:
            message: Message d'alerte
        
        Returns:
            True si envoyé avec succès
        """
        logger.info(f"Envoi d'une alerte: {message[:50]}...")
        return await self.send_message(f"🔴 {message}")
    
    async def send_warning(self, message: str) -> bool:
        """
        Envoyer un avertissement (jaune)
        
        Args:
            message: Message d'avertissement
        
        Returns:
            True si envoyé avec succès
        """
        logger.info(f"Envoi d'un avertissement: {message[:50]}...")
        return await self.send_message(f"⚠️ {message}")
    
    async def send_success(self, message: str) -> bool:
        """
        Envoyer une notification de succès (vert)
        
        Args:
            message: Message de succès
        
        Returns:
            True si envoyé avec succès
        """
        logger.info(f"Envoi d'un succès: {message[:50]}...")
        return await self.send_message(f"✅ {message}")
    
    async def send_info(self, message: str) -> bool:
        """
        Envoyer une information générale (bleu)
        
        Args:
            message: Message d'information
        
        Returns:
            True si envoyé avec succès
        """
        logger.info(f"Envoi d'une info: {message[:50]}...")
        return await self.send_message(f"ℹ️ {message}")
    
    async def test_connection(self) -> bool:
        """
        Tester la connexion au bot Telegram
        
        Returns:
            True si la connexion fonctionne
        """
        try:
            url = f"{self.base_url}/getMe"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        bot_name = data.get('result', {}).get('username', 'Unknown')
                        logger.info(f"Connexion Telegram OK - Bot: @{bot_name}")
                        return True
                    else:
                        logger.error(f"Erreur de connexion Telegram: {response.status}")
                        return False
        
        except Exception as e:
            logger.error(f"Exception lors du test de connexion Telegram: {e}")
            return False
