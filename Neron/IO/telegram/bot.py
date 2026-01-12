import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

# Charger les variables depuis les fichiers .env
load_dotenv("/home/eleazar/Homebox_Neron/.env")
load_dotenv("/home/eleazar/Homebox_Neron/.env.global")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OLLAMA_MODEL = os.getenv("NERON_OLLAMA_MODEL", "modèle inconnu")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bonjour ! Nerón-Telegram est en ligne ✅")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Statut : tout est OK !")

async def model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🧠 Modèle utilisé : {OLLAMA_MODEL}")

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("model", model))

if __name__ == "__main__":
    print("Nerón-Telegram démarré...")
    app.run_polling()

