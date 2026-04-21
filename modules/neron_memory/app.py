from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import sqlite3
from contextlib import contextmanager
from typing import Optional, List, Dict
import logging
import os
import json

# Configuration du logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Néron Memory",
    description="Service de mémoire persistante",
    version="0.2.0"
)

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "memory.db")


@contextmanager
def get_db():
    """Context manager thread-safe pour SQLite"""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_database():
    """Initialise la base de données"""
    logger.info("Initializing database...")
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
    logger.info("Database initialized successfully")


# Initialisation au démarrage
init_database()


class MemoryItem(BaseModel):
    input: str
    response: str
    metadata: Optional[Dict] = {}


class MemoryEntry(BaseModel):
    id: int
    input: str
    response: str
    metadata: Dict
    timestamp: str


@app.get("/")
def root():
    return {
        "service": "Néron Memory",
        "version": "0.2.0",
        "status": "active"
    }


@app.get("/health")
def health():
    """Healthcheck endpoint pour Docker"""
    try:
        with get_db() as conn:
            count = conn.execute("SELECT COUNT(*) as count FROM memory").fetchone()["count"]
        return {
            "status": "healthy",
            "entries": count
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@app.post("/store")
def store(item: MemoryItem):
    """Stocke une nouvelle entrée en mémoire"""
    logger.info(f"Storing new memory: {item.input[:50]}...")
    
    try:
        with get_db() as conn:
            cursor = conn.execute(
                "INSERT INTO memory (input, response, metadata) VALUES (?, ?, ?)",
                (
                    item.input,
                    item.response,
                    json.dumps(item.metadata) if item.metadata else "{}"
                )
            )
            conn.commit()
            entry_id = cursor.lastrowid
            
        logger.info(f"Memory stored successfully with ID: {entry_id}")
        return {
            "status": "ok",
            "id": entry_id
        }
    
    except Exception as e:
        logger.error(f"Failed to store memory: {e}")
        raise HTTPException(500, f"Storage error: {str(e)}")


@app.get("/retrieve", response_model=List[MemoryEntry])
def retrieve(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    """Récupère les dernières entrées de mémoire"""
    logger.info(f"Retrieving memories: limit={limit}, offset={offset}")
    
    try:
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT id, input, response, metadata, timestamp
                FROM memory
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset)
            ).fetchall()
            
            memories = []
            for row in rows:
                try:
                    metadata = json.loads(row["metadata"]) if row["metadata"] else {}
                except json.JSONDecodeError:
                    metadata = {}
                
                memories.append(MemoryEntry(
                    id=row["id"],
                    input=row["input"],
                    response=row["response"],
                    metadata=metadata,
                    timestamp=row["timestamp"]
                ))
            
            logger.info(f"Retrieved {len(memories)} memories")
            return memories
    
    except Exception as e:
        logger.error(f"Failed to retrieve memories: {e}")
        raise HTTPException(500, f"Retrieval error: {str(e)}")


@app.get("/search", response_model=List[MemoryEntry])
def search(
    query: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=100)
):
    """Recherche dans les mémoires par mot-clé"""
    logger.info(f"Searching memories for: {query}")
    
    try:
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT id, input, response, metadata, timestamp
                FROM memory
                WHERE input LIKE ? OR response LIKE ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (f"%{query}%", f"%{query}%", limit)
            ).fetchall()
            
            memories = []
            for row in rows:
                try:
                    metadata = json.loads(row["metadata"]) if row["metadata"] else {}
                except json.JSONDecodeError:
                    metadata = {}
                
                memories.append(MemoryEntry(
                    id=row["id"],
                    input=row["input"],
                    response=row["response"],
                    metadata=metadata,
                    timestamp=row["timestamp"]
                ))
            
            logger.info(f"Found {len(memories)} matching memories")
            return memories
    
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(500, f"Search error: {str(e)}")


@app.get("/stats")
def stats():
    """Statistiques de la mémoire"""
    try:
        with get_db() as conn:
            total = conn.execute("SELECT COUNT(*) as count FROM memory").fetchone()["count"]
            
            recent = conn.execute(
                "SELECT COUNT(*) as count FROM memory WHERE timestamp > datetime('now', '-7 days')"
            ).fetchone()["count"]
            
            oldest = conn.execute(
                "SELECT timestamp FROM memory ORDER BY id ASC LIMIT 1"
            ).fetchone()
            
            newest = conn.execute(
                "SELECT timestamp FROM memory ORDER BY id DESC LIMIT 1"
            ).fetchone()
        
        return {
            "total_entries": total,
            "recent_entries_7d": recent,
            "oldest_entry": oldest["timestamp"] if oldest else None,
            "newest_entry": newest["timestamp"] if newest else None
        }
    
    except Exception as e:
        logger.error(f"Stats failed: {e}")
        raise HTTPException(500, f"Stats error: {str(e)}")


@app.delete("/clear")
def clear_all():
    """⚠️ DANGER: Efface toute la mémoire"""
    logger.warning("CLEARING ALL MEMORY!")
    
    try:
        with get_db() as conn:
            conn.execute("DELETE FROM memory")
            conn.commit()
        
        logger.info("All memory cleared")
        return {"status": "ok", "message": "All memory cleared"}
    
    except Exception as e:
        logger.error(f"Clear failed: {e}")
        raise HTTPException(500, f"Clear error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
