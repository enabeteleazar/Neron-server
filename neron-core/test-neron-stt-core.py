#!/usr/bin/env python3
import requests
import os
import subprocess

# --- Chemin vers le fichier WAV de test ---
audio_file = "0001.mp3"

# --- Générer un fichier WAV de test si absent ---
if not os.path.exists(audio_file):
    print("[INFO] Fichier test.wav absent, génération d'un signal de test...")
    subprocess.run([
        "ffmpeg", "-f", "lavfi", "-i",
        "sine=frequency=440:duration=2", audio_file
    ], check=True)
    print("[INFO] test.wav créé avec succès.")

# --- URL de Neron-STT ---
stt_url = "http://localhost:8001/speech"

# --- Envoi du fichier WAV à Neron-STT ---
with open(audio_file, "rb") as f:
    files = {"file": f}
    try:
        response = requests.post(stt_url, files=files)
        response.raise_for_status()
        data = response.json()
        print("\n✅ Transcription reçue :")
        print(data.get("text", "Aucune transcription"))
    except requests.exceptions.RequestException as e:
        print("[ERREUR] Impossible de contacter Neron-STT :", e)
