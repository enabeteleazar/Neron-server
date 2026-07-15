from __future__ import annotations

import os
import struct
import tempfile
import time
import wave

from voice.config import SttConfig
from voice.models import TranscriptionResult
from voice.stt.providers.base import SttProvider


class FasterWhisperProvider(SttProvider):
    def __init__(self, config: SttConfig) -> None:
        self.config = config
        self._model = None

    def load(self) -> object:
        from faster_whisper import WhisperModel

        self._model = WhisperModel(
            self.config.model,
            device="cpu",
            compute_type="int8",
            download_root=self.config.download_root,
        )
        self._warmup()
        return self._model

    def is_ready(self) -> bool:
        return self._model is not None

    def transcribe_file(self, path: str) -> TranscriptionResult:
        if self._model is None:
            raise RuntimeError("Modèle STT non chargé")

        start = time.monotonic()
        kwargs = {"beam_size": 5}
        if self.config.language:
            kwargs["language"] = self.config.language

        segments, info = self._model.transcribe(path, **kwargs)
        raw_text = " ".join(seg.text.strip() for seg in segments).strip()
        latency_ms = round((time.monotonic() - start) * 1000, 2)
        return TranscriptionResult(
            text=raw_text,
            language=getattr(info, "language", None),
            confidence=None,
            metadata={
                "raw_text": raw_text,
                "stt_model": self.config.model,
                "duration_ms": latency_ms,
                "latency_ms": latency_ms,
            },
        )

    def _warmup(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
            with wave.open(tmp_path, "w") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(struct.pack("<" + "h" * 1600, *([0] * 1600)))
        try:
            if self._model is not None:
                list(self._model.transcribe(tmp_path, language="fr"))
        except Exception:
            pass
        finally:
            os.remove(tmp_path)
