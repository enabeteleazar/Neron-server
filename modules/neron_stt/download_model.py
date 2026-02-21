import os
import sys
model_name = os.getenv("WHISPER_MODEL", "base")
print(f"Telechargement faster-whisper '{model_name}'...")
from faster_whisper import WhisperModel
WhisperModel(model_name, device="cpu", compute_type="int8", download_root="/app/models")
print("Modele telecharge.")
