# agents/memory_agent.py
# Neron Core - Memory direct SQLite (sans neron_memory intermédiaire)

import sqlite3
import json
import os
import logging
from contextlib import contextmanager
from typing import Optional, List, Dict

logger = logging.getLogger("memory_agent")

DB_PATH = os.getenv("MEMORY_DB_PATH", "/mnt/usb-storage/Neron_AI/data/memory.db")


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialise la base de données (appelé au démarrage de core)"""
    logger.info(f"Memory DB init : {DB_PATH}")
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                input TEXT NOT NULL,
                response TEXT NOT NULL,
                metadata TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON memory(timestamp)")
        conn.commit()
    logger.info("Memory DB prête")


class MemoryAgent:
    """Accès direct SQLite — remplace les appels HTTP à neron_memory:8002"""

    def store(self, input_text: str, response: str, metadata: dict = None) -> int:
        try:
            with get_db() as conn:
                cursor = conn.execute(
                    "INSERT INTO memory (input, response, metadata) VALUES (?, ?, ?)",
                    (input_text, response, json.dumps(metadata or {}))
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Memory store error : {e}")
            return -1

    def retrieve(self, limit: int = 3) -> List[Dict]:
        try:
            with get_db() as conn:
                rows = conn.execute(
                    "SELECT id, input, response, metadata, timestamp FROM memory ORDER BY id DESC LIMIT ?",
                    (limit,)
                ).fetchall()
                return [self._row_to_dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Memory retrieve error : {e}")
            return []

    def search(self, query: str, limit: int = 3) -> List[Dict]:
        try:
            with get_db() as conn:
                rows = conn.execute(
                    """SELECT id, input, response, metadata, timestamp FROM memory
                       WHERE input LIKE ? OR response LIKE ?
                       ORDER BY id DESC LIMIT ?""",
                    (f"%{query}%", f"%{query}%", limit)
                ).fetchall()
                return [self._row_to_dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Memory search error : {e}")
            return []

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
            "timestamp": row["timestamp"]
        }
