from __future__ import annotations

from pathlib import Path

from voice.audio.codecs import SUPPORTED_AUDIO_EXTENSIONS


def validate_audio_input(audio: bytes, filename: str, max_size_mb: int) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_AUDIO_EXTENSIONS:
        raise ValueError(f"Format non supporté : '{ext}'")

    max_size_bytes = int(float(max_size_mb) * 1024 * 1024)
    if len(audio) > max_size_bytes:
        raise ValueError(
            f"Fichier trop volumineux : {len(audio) // 1024 // 1024}MB > {float(max_size_mb)}MB"
        )
    return ext
