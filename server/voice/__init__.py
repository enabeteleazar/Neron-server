"""Reusable voice subsystem for NeronOS."""

from voice import stt, tts
from voice.models import SpeechResult, TranscriptionResult

__all__ = ["SpeechResult", "TranscriptionResult", "stt", "tts"]
