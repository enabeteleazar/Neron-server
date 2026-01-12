from dotenv import load_dotenv
import os
import httpx
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# Charger le fichier .env
load_dotenv(dotenv_path="/home/eleazar/homebox/.env")

# Token Telegram
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# URL de Ollama et modèle
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# Vérification
if TOKEN is None:
    raise ValueError("TELEGRAM_BOT_TOKEN n'est pas défini dans le fichier .env")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    # Préparer la requête pour Ollama
    payload = {
        "model": MODEL,
        "prompt": user_text,
        "stream": False  # Désactiver le streaming pour simplifier
    }
    
    try:
        # Utiliser httpx pour les requêtes asynchrones
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(OLLAMA_URL, json=payload)
            resp.raise_for_status()
            
            # Ollama renvoie la réponse dans le champ "response"
            data = resp.json()
            text = data.get("response", "Pas de réponse d'Ollama.")
            
    except httpx.TimeoutException:
        text = "⏱️ Timeout : Ollama met trop de temps à répondre."
    except httpx.HTTPStatusError as e:
        text = f"❌ Erreur HTTP {e.response.status_code} : {e.response.text}"
    except Exception as e:
        text = f"❌ Erreur Ollama : {str(e)}"
    
    # Répondre sur Telegram
    await update.message.reply_text(text)

async def handle_message_streaming(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Version alternative avec streaming et mise à jour progressive"""
    user_text = update.message.text
    
    payload = {
        "model": MODEL,
        "prompt": user_text,
        "stream": True
    }
    
    try:
        full_response = ""
        message = await update.message.reply_text("🤔 Réflexion en cours...")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", OLLAMA_URL, json=payload) as resp:
                resp.raise_for_status()
                
                async for line in resp.aiter_lines():
                    if line.strip():
                        try:
                            chunk = json.loads(line)
                            if "response" in chunk:
                                full_response += chunk["response"]
                                
                                # Mettre à jour le message tous les 20 caractères
                                if len(full_response) % 20 == 0:
                                    await message.edit_text(full_response[:4000])  # Limite Telegram
                        except json.JSONDecodeError:
                            continue
        
        # Message final
        if full_response:
            await message.edit_text(full_response[:4000])
        else:
            await message.edit_text("Pas de réponse d'Ollama.")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur : {str(e)}")

# Initialiser le bot Telegram
app = ApplicationBuilder().token(TOKEN).build()

# Choisir la version simple ou avec streaming
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
# Pour activer le streaming, remplacer par :
# app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message_streaming))

print("🤖 Bot Telegram Ollama en cours d'exécution...")
app.run_polling()
