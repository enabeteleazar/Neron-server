from __future__ import annotations

import re

_SPACING_RE = re.compile(r"\s+")
_SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,.!?;:])")
_NERON_RE = re.compile(r"\b(?:neron|néron)\b", re.IGNORECASE)
_OK_RE = re.compile(r"\bok\b", re.IGNORECASE)


def normalize_french_text(text: str) -> str:
    normalized = _SPACING_RE.sub(" ", text or "").strip()
    normalized = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", normalized)
    normalized = _NERON_RE.sub("Néron", normalized)
    normalized = _OK_RE.sub("OK", normalized)
    if normalized and normalized[0].islower():
        normalized = normalized[0].upper() + normalized[1:]
    return normalized
