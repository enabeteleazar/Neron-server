"""
neron/sessions.py
=================
Gestion des sessions — persistance JSONL, overflow, pruning.
Inspiré d'OpenClaw : append-on-write, replay-on-read.

Chaque session = un fichier ~/.neron/sessions/<id>.jsonl
Format ligne :
  {"role": "user",      "content": "...", "ts": 1234567890}
  {"role": "assistant", "content": "...", "ts": 1234567890}
  {"role": "tool",      "tool_use_id": "...", "content": "...", "ts": ...}

Overflow :
  Si l'historique dépasse max_tokens (estimé), on compacte
  les vieux tours en un résumé via le LLM (ou truncation simple si pas de LLM dispo).
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("neron.sessions")

SESSIONS_DIR = Path(os.getenv("NERON_SESSIONS_DIR", Path.home() / ".neron" / "sessions"))
MAX_HISTORY_TOKENS = int(os.getenv("NERON_MAX_HISTORY_TOKENS", "8000"))

# ──────────────────────────────────────────────────────────────────────────────
# Session
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Session:
    id: str
    system_prompt: str = "Tu es Neron, un assistant IA local connecté à NEXUS."
    history: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    pending_intent: str | None = None  # contexte pour l'injection de skills

    # ── Ajout de messages ───────────────────────────────────────────────────

    def add_user(self, content: str) -> None:
        self.history.append({
            "role": "user",
            "content": content,
            "ts": int(time.time()),
        })
        self.pending_intent = content  # pour sélection de skills

    def add_assistant(self, content: str) -> None:
        self.history.append({
            "role": "assistant",
            "content": content,
            "ts": int(time.time()),
        })

    def add_tool_result(self, tool_use_id: str, result: Any) -> None:
        self.history.append({
            "role": "tool",
            "tool_use_id": tool_use_id,
            "content": json.dumps(result, ensure_ascii=False),
            "ts": int(time.time()),
        })

    # ── Overflow / pruning ──────────────────────────────────────────────────

    def estimated_tokens(self) -> int:
        """Estimation grossière : 1 token ≈ 4 caractères."""
        total = len(self.system_prompt)
        for msg in self.history:
            total += len(str(msg.get("content", "")))
        return total // 4

    def prune_if_needed(self, max_tokens: int = MAX_HISTORY_TOKENS) -> bool:
        """
        Si overflow : supprime les 4 plus anciens tours (2 paires user/assistant).
        Retourne True si pruning effectué.
        """
        if self.estimated_tokens() <= max_tokens:
            return False
        removed = 0
        target = 4  # tours à supprimer
        while removed < target and self.history:
            self.history.pop(0)
            removed += 1
        logger.info("[%s] Pruning : %d tours supprimés", self.id, removed)
        return True

    def clear(self) -> None:
        self.history.clear()

    # ── Format pour LLM ────────────────────────────────────────────────────

    def messages_for_llm(self) -> list[dict]:
        """
        Filtre les clés internes (ts) et retourne le format attendu par les LLMs.
        """
        result = []
        for msg in self.history:
            role = msg["role"]
            content = msg.get("content", "")
            if role == "tool":
                result.append({
                    "role": "tool",
                    "tool_use_id": msg.get("tool_use_id", ""),
                    "content": content,
                })
            else:
                result.append({"role": role, "content": content})
        return result

# ──────────────────────────────────────────────────────────────────────────────
# SessionStore
# ──────────────────────────────────────────────────────────────────────────────

class SessionStore:
    """
    Gère le cycle de vie des sessions : création, lecture, écriture JSONL.
    Cache en mémoire pour les sessions actives.
    """

    def __init__(self, sessions_dir: Path | None = None) -> None:
        self.sessions_dir = sessions_dir or SESSIONS_DIR
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, Session] = {}

    # ── CRUD ────────────────────────────────────────────────────────────────

    def create(
        self,
        session_id: str,
        system_prompt: str | None = None,
        metadata: dict | None = None,
    ) -> Session:
        session = Session(
            id=session_id,
            system_prompt=system_prompt or "Tu es Neron, un assistant IA local.",
            metadata=metadata or {},
        )
        self._cache[session_id] = session
        # Écrit le header JSONL
        self._write_header(session)
        logger.info("Session créée : %s", session_id)
        return session

    def get(self, session_id: str) -> Session | None:
        if session_id in self._cache:
            return self._cache[session_id]
        # Tente de charger depuis le disque
        path = self._path(session_id)
        if path.exists():
            session = self._load(path)
            self._cache[session_id] = session
            return session
        return None

    def get_or_create(self, session_id: str, system_prompt: str | None = None) -> Session:
        session = self.get(session_id)
        if session is None:
            session = self.create(session_id, system_prompt=system_prompt)
        return session

    def save(self, session: Session) -> None:
        """Réécrit entièrement le fichier JSONL (plus simple que l'append pour les edits)."""
        path = self._path(session.id)
        with path.open("w", encoding="utf-8") as f:
            # Ligne header
            f.write(json.dumps({
                "_type": "session_header",
                "id": session.id,
                "system": session.system_prompt,
                "metadata": session.metadata,
                "saved_at": int(time.time()),
            }, ensure_ascii=False) + "\n")
            # Historique
            for msg in session.history:
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")
        logger.debug("Session sauvegardée : %s (%d tours)", session.id, len(session.history))

    def delete(self, session_id: str) -> bool:
        path = self._path(session_id)
        if path.exists():
            path.unlink()
        if session_id in self._cache:
            del self._cache[session_id]
            return True
        return False

    def list_all(self) -> list[Session]:
        sessions = []
        for path in sorted(self.sessions_dir.glob("*.jsonl")):
            sid = path.stem
            session = self.get(sid)
            if session:
                sessions.append(session)
        return sessions

    # ── Fichiers ────────────────────────────────────────────────────────────

    def _path(self, session_id: str) -> Path:
        # Sécurise le nom de fichier
        safe_id = "".join(c for c in session_id if c.isalnum() or c in "-_.")
        return self.sessions_dir / f"{safe_id}.jsonl"

    def _write_header(self, session: Session) -> None:
        path = self._path(session.id)
        with path.open("w", encoding="utf-8") as f:
            f.write(json.dumps({
                "_type": "session_header",
                "id": session.id,
                "system": session.system_prompt,
                "metadata": session.metadata,
                "created_at": int(time.time()),
            }, ensure_ascii=False) + "\n")

    def _load(self, path: Path) -> Session:
        session = Session(id=path.stem)
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("_type") == "session_header":
                    session.id = record.get("id", session.id)
                    session.system_prompt = record.get("system", session.system_prompt)
                    session.metadata = record.get("metadata", {})
                else:
                    session.history.append(record)
        logger.debug("Session chargée : %s (%d tours)", session.id, len(session.history))
        return session
