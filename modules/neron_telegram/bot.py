import os
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

NERON_CORE_URL = os.getenv("NERON_CORE_URL", "http://neron-core:8000")
NERON_MEMORY_URL = os.getenv("NERON_MEMORY_URL", "http://neron-memory:8002")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN manquant")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /start"""
    await update.message.reply_text(
        "🧠 **Néron Assistant**\n\n"
        "Je suis votre assistant IA personnel.\n\n"
        "Commandes:\n"
        "/start - Ce message\n"
        "/stats - Statistiques mémoire\n"
        "/help - Aide\n\n"
        "Envoyez-moi simplement un message pour discuter !",
        parse_mode='Markdown'
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /stats"""
    try:
        response = requests.get(f"{NERON_MEMORY_URL}/stats", timeout=5)
        if response.status_code == 200:
            data = response.json()
            await update.message.reply_text(
                f"📊 **Statistiques**\n\n"
                f"Total conversations: {data['total_entries']}\n"
                f"Cette semaine: {data['recent_entries_7d']}\n"
                f"Première: {data['oldest_entry']}\n"
                f"Dernière: {data['newest_entry']}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Impossible de récupérer les stats")
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur: {str(e)}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /help"""
    await update.message.reply_text(
        "🧠 **Aide Néron**\n\n"
        "Envoyez-moi simplement votre message et je vous répondrai.\n\n"
        "Exemples:\n"
        "• Bonjour Néron\n"
        "• Explique-moi la relativité\n"
        "• Raconte une blague\n\n"
        "Commandes disponibles:\n"
        "/start - Démarrer\n"
        "/stats - Voir les statistiques\n"
        "/help - Cette aide",
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère les messages texte"""
    user_message = update.message.text
    chat_id = update.message.chat_id
    
    logger.info(f"Message reçu de {chat_id}: {user_message[:50]}")
    
    # Indicateur "en train d'écrire"
    await update.message.chat.send_action("typing")
    
    try:
        response = requests.post(
            f"{NERON_CORE_URL}/input/text",
            json={"text": user_message},
            timeout=120
        )
        
        if response.status_code == 200:
            data = response.json()
            neron_response = data.get("response", "Désolé, je n'ai pas pu générer de réponse.")
            await update.message.reply_text(neron_response)
        else:
            await update.message.reply_text(f"❌ Erreur {response.status_code}")
            
    except requests.exceptions.Timeout:
        await update.message.reply_text("⏱️ Je prends trop de temps à répondre, réessayez...")
    except Exception as e:
        logger.error(f"Erreur: {e}")
        await update.message.reply_text(f"❌ Erreur: {str(e)}")

def main():
    """Démarre le bot"""
    logger.info("Démarrage du bot Telegram...")
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Commandes
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("help", help_command))
    
    # Messages texte
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Bot prêt !")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

