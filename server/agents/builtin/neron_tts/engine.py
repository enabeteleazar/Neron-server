# agents/neron_tts/engine.py
# Moteur TTS : Piper (synthèse neuronale, voix fr_FR-siwis-medium) + ffmpeg
# (conversion mp3). Remplace l'implémentation espeak-ng initiale — bien plus
# naturel, toujours 100% local/CPU (pas de dépendance cloud).
#
# Installation : pip install piper-tts (dans le venv neronOS).
# Le modèle de voix (~60 Mo) doit être pré-téléchargé (cette version de la
# CLI piper ne supporte pas de téléchargement automatique) :
#   python3 -m piper.download_voices --data-dir ~/.local/share/piper-voices fr_FR-siwis-medium

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from core.config import settings

DEFAULT_VOICE = "fr_FR-siwis-medium"
# Le tout premier appel peut télécharger le modèle (~60 Mo) en plus de
# synthétiser — on laisse large. Les appels suivants sont rapides (modèle
# mis en cache localement dans --data-dir).
SUBPROCESS_TIMEOUT_S = 300


def _find_piper_binary() -> str:
    # 1) PATH classique (fonctionne en lancement manuel/terminal).
    found = shutil.which("piper")
    if found:
        return found
    # 2) À côté de l'interpréteur Python courant (venv) — nécessaire quand
    # le service systemd lance .../venv/bin/python par chemin complet sans
    # que venv/bin soit dans /home/neron/.npm-global/bin:/home/neron/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin (cas fréquent : ExecStart=.../venv/bin/python
    # sans Environment=PATH= dédié).
    candidate = Path(sys.executable).parent / "piper"
    if candidate.exists():
        return str(candidate)
    raise RuntimeError(
        "piper introuvable (ni dans /home/neron/.npm-global/bin:/home/neron/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin, ni à côté de l'interpréteur Python "
        f"'{sys.executable}') — installe-le via 'pip install piper-tts' dans "
        "le venv utilisé par neronOS."
    )


def _voices_dir() -> Path:
    d = Path.home() / ".local" / "share" / "piper-voices"
    d.mkdir(parents=True, exist_ok=True)
    return d


class PiperFfmpegEngine:
    """Synthèse vocale neuronale via Piper + conversion mp3 via ffmpeg."""

    def __init__(self) -> None:
        self._piper_bin = _find_piper_binary()
        self._ffmpeg_bin = shutil.which("ffmpeg")
        if not self._ffmpeg_bin:
            raise RuntimeError(
                "ffmpeg introuvable — installe-le via 'sudo apt install ffmpeg'."
            )
        # TTS_VOICE n'existe pas forcément dans neron.yaml (settings) ;
        # on retombe sur la voix française par défaut si absent.
        self._voice = getattr(settings, "TTS_VOICE", None) or DEFAULT_VOICE
        self._voices_dir = _voices_dir()

    def name(self) -> str:
        return f"piper:{self._voice}"

    def synthesize(self, text: str, fmt: str = "mp3") -> tuple[bytes, str]:
        """
        Synthétise  en audio via Piper.

        Args:
            text: Texte à synthétiser (déjà validé/tronqué par TTSAgent).
            fmt: 'mp3' (défaut) ou 'wav'.

        Returns:
            (audio_bytes, mimetype)

        Raises:
            RuntimeError: si piper ou ffmpeg échoue.
        """
        with tempfile.TemporaryDirectory(prefix="neron_tts_") as tmpdir:
            wav_path = Path(tmpdir) / "out.wav"

            piper_cmd = [
                self._piper_bin,
                "--model", self._voice,
                "--data-dir", str(self._voices_dir),
                "--output_file", str(wav_path),
            ]
            result = subprocess.run(
                piper_cmd,
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=SUBPROCESS_TIMEOUT_S,
            )
            if result.returncode != 0 or not wav_path.exists():
                raise RuntimeError(
                    f"piper a échoué (code {result.returncode}) : "
                    f"{result.stderr.decode('utf-8', errors='replace')[:300]}"
                )

            if fmt == "wav":
                return wav_path.read_bytes(), "audio/wav"

            mp3_path = Path(tmpdir) / "out.mp3"
            ffmpeg_cmd = [
                self._ffmpeg_bin, "-y",
                "-i", str(wav_path),
                "-codec:a", "libmp3lame",
                "-qscale:a", "4",
                str(mp3_path),
            ]
            result = subprocess.run(
                ffmpeg_cmd, capture_output=True, timeout=30
            )
            if result.returncode != 0 or not mp3_path.exists():
                raise RuntimeError(
                    f"ffmpeg a échoué (code {result.returncode}) : "
                    f"{result.stderr.decode('utf-8', errors='replace')[:300]}"
                )

            return mp3_path.read_bytes(), "audio/mpeg"


_engine_instance: PiperFfmpegEngine | None = None


def get_engine() -> PiperFfmpegEngine:
    """
    Factory appelée par tts_agent.load_engine(). Instancie (une fois) et
    retourne le moteur TTS. Toute erreur (binaire absent, etc.) remonte à
    l'appelant, qui la logue sans bloquer le démarrage du reste de NeronOS.
    """
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = PiperFfmpegEngine()
    return _engine_instance

