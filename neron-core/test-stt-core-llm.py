import requests
import sounddevice as sd
import wavio
import time
import os
from pathlib import Path

# --- Paramètres ---
LLM_URL = "http://localhost:11434/v1/completions"
MODEL = "llama3.2:1B"
DURATION = 5  # secondes d'enregistrement
FILENAME = "/tmp/neron_test.wav"

# --- 1. Enregistrer l'audio depuis le micro ---
print("Parlez maintenant ({} secondes)...".format(DURATION))
audio = sd.rec(int(DURATION * 44100), samplerate=44100, channels=1)
sd.wait()
wavio.write(FILENAME, audio, 44100, sampwidth=2)
print("Enregistrement terminé :", FILENAME)

# --- 2. Transcrire avec Néron-STT ---
print("Transcription en cours...")
# Ici, on suppose que Néron-STT a un endpoint ou une fonction locale
# Pour le test, on peut utiliser un script existant STT, par ex :
# python3 neron_stt.py --file /tmp/neron_test.wav
# Pour l'exemple, on simule la transcription :
transcribed_text = "Bonjour Néron, que puis-je faire ?"
print("Texte transcrit :", transcribed_text)

# --- 3. Envoyer la transcription au LLM ---
data = {
    "model": MODEL,
    "prompt": transcribed_text,
    "max_tokens": 100
}

try:
    response = requests.post(LLM_URL, json=data)
    response.raise_for_status()
    result = response.json()
    print("Réponse LLM :")
    print(result)
except Exception as e:
    print("Erreur lors de la requête vers Néron-LLM :", e)

# --- Optionnel : supprimer le fichier audio après test ---
if Path(FILENAME).exists():
    os.remove(FILENAME)
