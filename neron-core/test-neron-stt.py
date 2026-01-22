# test_neron_stt.py
import requests
import os
import subprocess
import sys
import uuid


# Chemin vers un fichier audio valide pour le test
audio_file = sys.argv[1] if len(sys.argv) > 1 else "/usr/share/sounds/alsa/Front_Center.wav"

url = "http://localhost:8001/speech"

with open(audio_file, "rb") as f:
    files = {"file": (audio_file, f, "audio/wav")}
    response = requests.post(url, files=files)

if response.status_code == 200:
    print("✅ Transcription reçue :")
    print(response.json().get("text"))
else:
    print(f"❌ Erreur : {response.status_code}")
    print(response.text)
