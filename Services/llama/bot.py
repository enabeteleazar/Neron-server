import os
import httpx
import json
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

# Configuration du logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434/api/generate")
MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")

# Vérification
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN n'est pas défini")

logger.info(f"Bot configuré avec le modèle: {MODEL}")
logger.info(f"URL Ollama: {OLLAMA_URL}")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /start"""
    welcome_text = (
        "👋 Bonjour ! Je suis un bot alimenté par Ollama.\n\n"
        "Envoyez-moi n'importe quel message et je vous répondrai !\n\n"
        "Commandes disponibles:\n"
        "/start - Afficher ce message\n"
        "/help - Aide\n"
        "/model - Voir le modèle utilisé"
    )
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /help"""
    help_text = (
        "ℹ️ Comment utiliser ce bot:\n\n"
        "Envoyez simplement un message et j'utiliserai Ollama pour générer une réponse.\n\n"
        f"Modèle actuel: {MODEL}"
    )
    await update.message.reply_text(help_text)

async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /model"""
    await update.message.reply_text(f"🤖 Modèle utilisé: {MODEL}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère les messages texte"""
    user_text = update.message.text
    user_name = update.effective_user.first_name
    
    logger.info(f"Message de {user_name}: {user_text[:50]}...")
    
    # Préparer la requête pour Ollama
    payload = {
        "model": MODEL,
        "prompt": user_text,
        "stream": False
    }
    
    try:
        # Message de chargement
        loading_msg = await update.message.reply_text("🤔 Réflexion en cours...")
        
        # Requête vers Ollama
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(OLLAMA_URL, json=payload)
            resp.raise_for_status()
            
            data = resp.json()
            text = data.get("response", "Pas de réponse d'Ollama.")
            
            # Limiter à 4096 caractères (limite Telegram)
            if len(text) > 4000:
                text = text[:4000] + "\n\n... (réponse tronquée)"
            
            # Mettre à jour le message
            await loading_msg.edit_text(text)
            logger.info("Réponse envoyée avec succès")
            
    except httpx.TimeoutException:
        error_text = "⏱️ Timeout: Ollama met trop de temps à répondre."
        await loading_msg.edit_text(error_text)
        logger.error("Timeout Ollama")
        
    except httpx.HTTPStatusError as e:
        error_text = f"❌ Erreur HTTP {e.response.status_code}"
        await loading_msg.edit_text(error_text)
        logger.error(f"Erreur HTTP: {e.response.status_code} - {e.response.text}")
        
    except Exception as e:
        error_text = f"❌ Erreur: {str(e)}"
        await loading_msg.edit_text(error_text)
        logger.error(f"Erreur inattendue: {str(e)}")

def main():
    """Point d'entrée principal"""
    logger.info("Démarrage du bot Telegram...")
    
    # Initialiser le bot
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Ajouter les handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("model", model_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    # Démarrer le bot
    logger.info("🤖 Bot Telegram Ollama en cours d'exécution...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
