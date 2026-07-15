from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def find_ffmpeg() -> str:
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        raise RuntimeError("ffmpeg introuvable - installe-le via 'sudo apt install ffmpeg'.")
    return ffmpeg_bin


def convert_wav_to_mp3(wav_path: Path, mp3_path: Path) -> None:
    result = subprocess.run(
        [
            find_ffmpeg(),
            "-y",
            "-i",
            str(wav_path),
            "-codec:a",
            "libmp3lame",
            "-qscale:a",
            "4",
            str(mp3_path),
        ],
        capture_output=True,
        timeout=30,
    )
    if result.returncode != 0 or not mp3_path.exists():
        raise RuntimeError(
            f"ffmpeg a échoué (code {result.returncode}) : "
            f"{result.stderr.decode('utf-8', errors='replace')[:300]}"
        )
