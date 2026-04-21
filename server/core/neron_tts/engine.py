# neron_tts/engine.py
# Moteur TTS espeak + conversion MP3 via ffmpeg pour compatibilité Safari iOS

import logging
import tempfile
import os
import subprocess

logger = logging.getLogger("neron_tts")


class EspeakEngine:
    """Moteur TTS basé sur espeak + ffmpeg pour conversion MP3"""

    def __init__(self, language: str = "fr", rate: int = 150):
        self._language = language
        self._rate = rate

        result = subprocess.run(["which", "espeak"], capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError("espeak non trouvé — installez espeak")

        result = subprocess.run(["which", "ffmpeg"], capture_output=True, text=True)
        self._has_ffmpeg = result.returncode == 0
        if not self._has_ffmpeg:
            logger.warning("ffmpeg non trouvé — sortie WAV uniquement")

        logger.info(f"EspeakEngine prêt | langue: {language} | rate: {rate} | ffmpeg: {self._has_ffmpeg}")

    def name(self) -> str:
        return "espeak"

    def synthesize(self, text: str, format: str = "mp3") -> tuple:
        """
        Synthétise le texte.
        Retourne (audio_bytes, mimetype).
        """
        wav_path = None
        mp3_path = None

        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                wav_path = tmp.name

            result = subprocess.run(
                ["espeak", "-v", self._language, "-s", str(self._rate), "-w", wav_path, text],
                capture_output=True, text=True, timeout=30
            )

            if result.returncode != 0:
                raise RuntimeError(f"espeak erreur : {result.stderr}")

            if not os.path.exists(wav_path) or os.path.getsize(wav_path) == 0:
                raise RuntimeError("Fichier WAV vide")

            # Convertir en MP3 si ffmpeg disponible
            if format == "mp3" and self._has_ffmpeg:
                mp3_path = wav_path.replace(".wav", ".mp3")
                result = subprocess.run(
                    ["ffmpeg", "-y", "-i", wav_path,
                     "-codec:a", "libmp3lame", "-q:a", "4", "-ar", "22050",
                     mp3_path],
                    capture_output=True, text=True, timeout=30
                )

                if result.returncode == 0 and os.path.getsize(mp3_path) > 0:
                    with open(mp3_path, "rb") as f:
                        audio_bytes = f.read()
                    logger.info(f"Synthèse OK (MP3) : {len(audio_bytes)} bytes")
                    return audio_bytes, "audio/mpeg"
                else:
                    logger.warning(f"ffmpeg échoué, fallback WAV : {result.stderr}")

            # Fallback WAV
            with open(wav_path, "rb") as f:
                audio_bytes = f.read()
            logger.info(f"Synthèse OK (WAV) : {len(audio_bytes)} bytes")
            return audio_bytes, "audio/wav"

        finally:
            for path in [wav_path, mp3_path]:
                if path and os.path.exists(path):
                    os.remove(path)


def get_engine(language: str = "fr", rate: int = 150) -> EspeakEngine:
    return EspeakEngine(language=language, rate=rate)
