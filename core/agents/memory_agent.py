# core/agents/memory_agent.py
# Néron Core - Memory direct SQLite (avec support planner_tasks)

from __future__ import annotations
import json
import logging
import sqlite3
from contextlib import contextmanager
from typing import Dict, List, Optional

from core.config import settings

logger = logging.getLogger("memory_agent")

DB_PATH = str(settings.MEMORY_DB_PATH)
_MAX_MEMORY_ROWS = int(getattr(settings, "MEMORY_MAX_ROWS", 10_000))

# ── Connexion ────────────────────────────────────────────────

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ── Init ────────────────────────────────────────────────────

def init_db() -> None:
    """Initialise la base de données et toutes les tables."""
    logger.info("Memory DB init : %s", DB_PATH)
    with get_db() as conn:
        # Table échanges classiques
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                input     TEXT NOT NULL,
                response  TEXT NOT NULL,
                metadata  TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_timestamp ON memory(timestamp)")

        # Table planner tasks
        conn.execute("""
            CREATE TABLE IF NOT EXISTS planner_tasks (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                name      TEXT NOT NULL,
                agent     TEXT NOT NULL,
                payload   TEXT,
                state     TEXT,
                result    TEXT,
                error     TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_timestamp ON planner_tasks(timestamp)")

        # Table events
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                type      TEXT,
                service   TEXT,
                message   TEXT,
                data      TEXT
            )
        """)
        conn.commit()
    logger.info("Memory DB prête")


# ── MemoryAgent ─────────────────────────────────────────────

class MemoryAgent:
    """Accès direct SQLite — remplace les appels HTTP à neron_memory."""

    def reload(self) -> bool:
        """Réinitialise la base SQLite."""
        try:
            init_db()
            return True
        except Exception as e:
            logger.error("Memory reload error : %s", e)
            return False

    # ── Mémoire générale ─────────────────────────────

    def store(self, input_text: str, response: str, metadata: dict | None = None) -> int:
        try:
            with get_db() as conn:
                cursor = conn.execute(
                    "INSERT INTO memory (input, response, metadata) VALUES (?, ?, ?)",
                    (input_text, response, json.dumps(metadata or {})),
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error("Memory store error : %s", e)
            return -1

    def retrieve(self, limit: int = 3) -> List[Dict]:
        try:
            with get_db() as conn:
                rows = conn.execute(
                    "SELECT id, input, response, metadata, timestamp FROM memory "
                    "ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
                return [self._row_to_dict(r) for r in rows]
        except Exception as e:
            logger.error("Memory retrieve error : %s", e)
            return []

    def search(self, query: str, limit: int = 3) -> List[Dict]:
        try:
            with get_db() as conn:
                rows = conn.execute(
                    """SELECT id, input, response, metadata, timestamp FROM memory
                       WHERE input LIKE ? OR response LIKE ?
                       ORDER BY id DESC LIMIT ?""",
                    (f"%{query}%", f"%{query}%", limit),
                ).fetchall()
                return [self._row_to_dict(r) for r in rows]
        except Exception as e:
            logger.error("Memory search error : %s", e)
            return []

    def cleanup(self, days: int = 30) -> int:
        deleted = 0
        try:
            with get_db() as conn:
                cursor = conn.execute(
                    "DELETE FROM memory WHERE timestamp < datetime('now', ? )",
                    (f"-{days} days",),
                )
                deleted += cursor.rowcount

                count = conn.execute("SELECT COUNT(*) FROM memory").fetchone()[0]
                if count > _MAX_MEMORY_ROWS:
                    overflow = count - _MAX_MEMORY_ROWS
                    cursor = conn.execute(
                        "DELETE FROM memory WHERE id IN "
                        "(SELECT id FROM memory ORDER BY id ASC LIMIT ?)",
                        (overflow,),
                    )
                    deleted += cursor.rowcount
                conn.commit()
            logger.info("Memory cleanup : %d entrées supprimées", deleted)
        except Exception as e:
            logger.error("Memory cleanup error : %s", e)
        return deleted

    def count(self) -> int:
        try:
            with get_db() as conn:
                return conn.execute("SELECT COUNT(*) FROM memory").fetchone()[0]
        except Exception as e:
            logger.error("Memory count error : %s", e)
            return 0

    # ── Planner tasks ────────────────────────────────

    def store_task(self, task: dict) -> int:
        """Persiste une tâche du planner."""
        try:
            with get_db() as conn:
                cursor = conn.execute(
                    "INSERT INTO planner_tasks (name, agent, payload, state, result, error) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        task.get("name"),
                        task.get("agent"),
                        json.dumps(task.get("payload", {})),
                        task.get("state"),
                        task.get("result"),
                        task.get("error"),
                    ),
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error("Planner store_task error : %s", e)
            return -1

    def get_tasks_history(self, limit: int = 50) -> List[Dict]:
        try:
            with get_db() as conn:
                rows = conn.execute(
                    "SELECT * FROM planner_tasks ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
                return [self._task_row_to_dict(r) for r in rows]
        except Exception as e:
            logger.error("Planner get_tasks_history error : %s", e)
            return []

    def _task_row_to_dict(self, row) -> Dict:
        try:
            payload = json.loads(row["payload"]) if row["payload"] else {}
        except Exception:
            payload = {}
        return {
            "id": row["id"],
            "name": row["name"],
            "agent": row["agent"],
            "payload": payload,
            "state": row["state"],
            "result": row["result"],
            "error": row["error"],
            "timestamp": row["timestamp"]
        }

    def _row_to_dict(self, row) -> Dict:
        try:
            metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        except Exception:
            metadata = {}
        return {
            "id": row["id"],
            "input": row["input"],
            "response": row["response"],
            "metadata": metadata,
            "timestamp": row["timestamp"],
        }
