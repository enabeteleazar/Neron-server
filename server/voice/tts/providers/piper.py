from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from voice.audio.codecs import MIMETYPE_BY_FORMAT
from voice.audio.converters import convert_wav_to_mp3
from voice.config import TtsConfig
from voice.models import SpeechResult
from voice.tts.providers.base import TtsProvider

SUBPROCESS_TIMEOUT_S = 300


def _find_piper_binary() -> str:
    found = shutil.which("piper")
    if found:
        return found
    candidate = Path(sys.executable).parent / "piper"
    if candidate.exists():
        return str(candidate)
    raise RuntimeError(
        "piper introuvable (ni dans PATH, ni à côté de l'interpréteur Python "
        f"'{sys.executable}') - installe-le via 'pip install piper-tts'."
    )


def _voices_dir() -> Path:
    directory = Path.home() / ".local" / "share" / "piper-voices"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


class PiperFfmpegProvider(TtsProvider):
    def __init__(self, config: TtsConfig) -> None:
        self.config = config
        self._piper_bin = _find_piper_binary()
        self._voices_dir = _voices_dir()

    def name(self) -> str:
        return f"piper:{self.config.voice}"

    def synthesize(self, text: str, fmt: str = "mp3") -> SpeechResult:
        with tempfile.TemporaryDirectory(prefix="neron_tts_") as tmpdir:
            wav_path = Path(tmpdir) / "out.wav"
            result = subprocess.run(
                [
                    self._piper_bin,
                    "--model",
                    self.config.voice,
                    "--data-dir",
                    str(self._voices_dir),
                    "--output_file",
                    str(wav_path),
                ],
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
                return SpeechResult(
                    audio=wav_path.read_bytes(),
                    format="wav",
                    metadata={"mimetype": MIMETYPE_BY_FORMAT["wav"], "engine": self.name()},
                )

            mp3_path = Path(tmpdir) / "out.mp3"
            convert_wav_to_mp3(wav_path, mp3_path)
            return SpeechResult(
                audio=mp3_path.read_bytes(),
                format="mp3",
                metadata={"mimetype": MIMETYPE_BY_FORMAT["mp3"], "engine": self.name()},
            )
