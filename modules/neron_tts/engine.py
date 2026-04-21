# modules/neron_tts/engine.py
# Adapter TTS - pattern interface/implementation

import os
import tempfile
import logging

logger = logging.getLogger("neron_tts.engine")


class TTSEngine:
    """Interface de base - tous les moteurs TTS implementent cette classe"""

    def synthesize(self, text: str) -> bytes:
        raise NotImplementedError

    def name(self) -> str:
        raise NotImplementedError


class Pyttsx3Engine(TTSEngine):
    """Moteur TTS offline via pyttsx3"""

    def __init__(self):
        import pyttsx3
        self.engine = pyttsx3.init()

        # Configuration voix francaise
        lang = os.getenv("TTS_LANGUAGE", "fr")
        rate = int(os.getenv("TTS_RATE", "150"))
        volume = float(os.getenv("TTS_VOLUME", "1.0"))

        self.engine.setProperty("rate", rate)
        self.engine.setProperty("volume", volume)

        # Chercher une voix francaise si disponible
        voices = self.engine.getProperty("voices")
        for voice in voices:
            if "french" in voice.name.lower() or lang in voice.id.lower():
                self.engine.setProperty("voice", voice.id)
                logger.info(f"Voix selectionnee : {voice.id}")
                break

        self._lang = "fr" if lang == "fr" else lang
        self._rate = rate
        logger.info(f"Pyttsx3Engine init : rate={rate}, volume={volume}, lang={lang}")

    def synthesize(self, text: str) -> bytes:
        import subprocess
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp_path = f.name

            # espeak CLI — plus fiable que pyttsx3 save_to_file
            result = subprocess.run(
                ["espeak", "-v", self._lang, "-s", str(self._rate), "-w", tmp_path, text],
                capture_output=True, timeout=30
            )

            if result.returncode != 0:
                raise RuntimeError(f"espeak error: {result.stderr.decode()}")

            with open(tmp_path, "rb") as f:
                audio_bytes = f.read()

            logger.info(f"Synthese OK : {len(text)} chars -> {len(audio_bytes)} bytes")
            return audio_bytes

        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

    def name(self) -> str:
        return "pyttsx3"


def get_engine() -> TTSEngine:
    """Factory - retourne le moteur configure par TTS_ENGINE"""
    engine_name = os.getenv("TTS_ENGINE", "pyttsx3")

    if engine_name == "pyttsx3":
        return Pyttsx3Engine()

    raise ValueError(f"Moteur TTS inconnu : '{engine_name}'")
